# API 配置
BASE_URL = "http://172.18.0.1:8000"  # Docker 容器访问宿主机
CACHE_DIR = "/astrbot/data/plugins/genie_tts_cache"

# 120字约为 22s -> 每秒约 5.45 字
CHARS_PER_SEC = 120 / 22

# 角色映射表
CHARACTERS = {
    "feibi": {
        "load": {
            "character_name": "feibi",
            "onnx_model_dir": "/root/genie/CharacterModels/v2ProPlus/feibi/tts_models",
            "language": "zh"
        },
        "ref": {
            "character_name": "feibi",
            "audio_path": "/root/genie/CharacterModels/v2ProPlus/feibi/prompt_wav/zh_vo_Main_Linaxita_2_1_10_26.wav",
            "audio_text": "在此之前,请您务必继续享受旅居拉古那的时光。",
            "language": "zh"
        }
    },
    "siki": {
        "load": {
            "character_name": "siki",
            "onnx_model_dir": "/root/genie/CharacterModels/v2ProPlus/siki/tts_models",
            "language": "ja"
        },
        "ref": {
            "character_name": "siki",
            "audio_path": "/root/genie/CharacterModels/v2ProPlus/siki/prompt_wav/Henji.wav",
            "audio_text": "返事なかったから、誰にも言ってない。",
            "language": "ja"
        }
    },
    "tomori": {
        "load": {
            "character_name": "tomori",
            "onnx_model_dir": "/root/genie/CharacterModels/v2ProPlus/tomori/tts_models",
            "language": "jp"
        },
        "ref": {
            "character_name": "tomori",
            "audio_path": "/root/genie/CharacterModels/v2ProPlus/tomori/prompt_wav/1.wav",
            "audio_text": "あのちゃん。もう一回説明、聞きたい……途中からわからなくなって……",
            "language": "jp"
        }
    },
    "taffy": {
        "load": {
            "character_name": "taffy",
            "onnx_model_dir": "/root/genie/CharacterModels/v2ProPlus/taffy/tts_models",
            "language": "zh"
        },
        "ref": {
            "character_name": "taffy",
            "audio_path": "/root/genie/CharacterModels/v2ProPlus/taffy/prompt_wav/Taffy_120.wav",
            "audio_text": "地板上有反光，不够亮。",
            "language": "zh"
        }
    }
}

DEFAULT_CHARACTER = "feibi"
