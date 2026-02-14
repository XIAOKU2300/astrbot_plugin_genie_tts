import asyncio
import logging
import os
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.provider import LLMResponse
from astrbot.api.message_components import Record

from .tts_engine import TTSEngine
from .config import CHARS_PER_SEC, DEFAULT_CHARACTER

logger = logging.getLogger("astrbot")

@register(
    "genie_tts", 
    "YourName", 
    "GenieTTS 语音回复插件 - 鸣潮UI风格双方案转码", 
    "1.1.0"
)
class GenieTTSPlugin(Star):
    def __init__(self, context: Context, config: dict = None) -> None:
        super().__init__(context)
        self.engine = TTSEngine()
        self.queue = asyncio.Queue()
        self.is_processing = False
        self.worker_task = None
        self.enabled = True
        self.user_pref = {}

    async def initialize(self) -> None:
        logger.info("[GenieTTS] 正在启动语音合成后台队列...")
        self.worker_task = asyncio.create_task(self._worker())

    async def terminate(self) -> None:
        self.enabled = False
        if self.worker_task:
            self.worker_task.cancel()
        logger.info("[GenieTTS] 插件已卸载")

    @filter.on_llm_response()
    async def on_ai_reply(self, event: AstrMessageEvent, resp: LLMResponse) -> None:
        if not self.enabled: return
        resp_text = resp.completion_text
        if not resp_text or len(resp_text.strip()) < 1: return

        user_id = event.get_sender_id()
        char_name = self.user_pref.get(user_id, DEFAULT_CHARACTER)
        est_time = len(resp_text) / CHARS_PER_SEC

        await self.queue.put({
            "text": resp_text,
            "event": event,
            "est_time": est_time,
            "character": char_name
        })

    async def _worker(self):
        """后台队列处理逻辑"""
        while True:
            try:
                task = await self.queue.get()
                self.is_processing = True

                text = task["text"]
                event: AstrMessageEvent = task["event"]
                char_name = task["character"]

                # 转换音频
                audio_path = await self.engine.generate_tts(text, char_name)

                if audio_path and os.path.exists(audio_path):
                    # 1. 构造语音组件
                    voice_msg = Record(file=audio_path)
                    
                    # 2. 【终极修复】手动构建 Result 对象，直接操作 chain 列表
                    # 不要使用 .message()，因为它底层会强制转成 Plain 文本组件
                    result_wrapper = MessageEventResult()
                    result_wrapper.chain.append(voice_msg) 
                    
                    try:
                        # 3. 发送
                        await self.context.send_message(
                            event.unified_msg_origin,
                            result_wrapper
                        )
                        logger.info(f"[GenieTTS] 语音成功下发: {char_name}")
                    except Exception as e:
                        logger.error(f"[GenieTTS] 消息接口调用失败: {e}")
                
                # 语速停顿
                await asyncio.sleep(task["est_time"] * 0.3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[GenieTTS] Worker 运行异常: {e}", exc_info=True)
            finally:
                self.is_processing = False
                self.queue.task_done()

    @filter.command("tts")
    async def cmd_tts_control(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        parts = msg.split()
        result = MessageEventResult()
        
        if len(parts) < 2:
            return result.message(f"TTS 状态: {'开启' if self.enabled else '关闭'}")

        cmd = parts[1].lower()
        if cmd == "on":
            self.enabled = True
            return result.message("已开启")
        elif cmd == "off":
            self.enabled = False
            return result.message("已关闭")
        elif cmd == "set" and len(parts) > 2:
            char = parts[2].lower()
            self.user_pref[event.get_sender_id()] = char
            return result.message(f"音色已设为: {char}")
        
        return result.message("指令有误。")