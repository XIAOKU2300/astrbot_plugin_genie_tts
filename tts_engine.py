import os
import hashlib
import httpx
import asyncio
import logging
import time
from .config import BASE_URL, CACHE_DIR, CHARACTERS

logger = logging.getLogger("astrbot")

class TTSEngine:
    def __init__(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)
        self.loaded_characters = set()

    def _get_cache_path(self, text, char_name):
        """生成缓存文件路径"""
        md5 = hashlib.md5(f"{char_name}_{text}".encode('utf-8')).hexdigest()
        # 必须使用绝对路径，确保 FFmpeg 和 AstrBot 都能准备找到文件
        return os.path.abspath(os.path.join(CACHE_DIR, f"{md5}.mp3"))

    async def _ensure_character_loaded(self, char_name):
        """对应 Yunzai 中的 ensureModelLoaded"""
        if char_name in self.loaded_characters:
            return True

        cfg = CHARACTERS.get(char_name)
        if not cfg:
            logger.error(f"角色 {char_name} 不在配置中")
            return False

        try:
            async with httpx.AsyncClient() as client:
                # 1. 对应 load 接口
                await client.post(f"{BASE_URL}/load_character", json=cfg.get("load", {}), timeout=30)
                # 2. 对应 set_reference_audio 接口
                await client.post(f"{BASE_URL}/set_reference_audio", json=cfg.get("ref", {}), timeout=30)
            
            self.loaded_characters.add(char_name)
            return True
        except Exception as e:
            logger.error(f"加载角色失败: {e}")
            return False

    async def _convert_audio(self, input_path, output_path):
        """
        核心复现：Yunzai 插件中的双方案 FFmpeg 转换逻辑
        """
        # --- 方案 A：标准转换 (对应 JS 中的第一个 execPromise) ---
        # 假设文件带有标准的 WAV/MP3 格式头
        cmd_a = [
            'ffmpeg', '-i', input_path, '-y',
            '-acodec', 'libmp3lame', '-ab', '128k', output_path
        ]
        
        logger.info(f"方案 A 尝试标准转换...")
        process = await asyncio.create_subprocess_exec(
            *cmd_a,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        if process.returncode == 0 and os.path.exists(output_path):
            logger.info("方案 A 转换成功")
            return True

        # --- 方案 B：强制 PCM 转换 (对应 JS 中的 catch 后续逻辑) ---
        # 针对后端返回无头原始采样数据的情况 (s16le, 32000Hz, 单声道)
        logger.warning("方案 A 失败，尝试方案 B (强制 PCM 模式)...")
        cmd_b = [
            'ffmpeg', '-f', 's16le', '-ar', '32000', '-ac', '1',
            '-i', input_path, '-y', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd_b,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        if process.returncode == 0 and os.path.exists(output_path):
            logger.info("方案 B 转换成功")
            return True
        
        logger.error("所有转码方案均已失败")
        return False

    async def generate_tts(self, text, char_name=None):
        """对应 Yunzai 中的 generateVoice"""
        char_name = char_name or "feibi"
        target_mp3 = self._get_cache_path(text, char_name)

        if os.path.exists(target_mp3):
            return target_mp3

        if not await self._ensure_character_loaded(char_name):
            return None

        # 临时文件名，对应 vits_${Date.now()}.wav
        temp_wav = os.path.join(CACHE_DIR, f"temp_{int(time.time() * 1000)}.wav")

        try:
            payload = {
                "character_name": char_name,
                "text": text,
                "split_sentence": False,
                "save_path": ""
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(f"{BASE_URL}/tts", json=payload, timeout=120)
                if response.status_code != 200:
                    return None
                
                # 写入原始二进制数据
                with open(temp_wav, 'wb') as f:
                    f.write(response.content)

            # 调用双方案转换
            success = await self._convert_audio(temp_wav, target_mp3)
            
            if success:
                return target_mp3
            return None

        except Exception as e:
            logger.error(f"TTS 生成任务出错: {e}")
            return None
        finally:
            # 转换结束后立即清理原始临时文件
            if os.path.exists(temp_wav):
                os.remove(temp_wav)