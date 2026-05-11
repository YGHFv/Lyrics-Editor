# Lyrics Editor

本项目用于处理本地音乐文件：读取歌曲元数据，匹配在线歌词，保存 LRC，并为后续“用语音识别文本修正时间轴”和“逐字歌词/卡拉 OK 歌词”对齐打基础。

设计上参考了 [LDDC](https://github.com/chenmozhijin/LDDC) 的能力方向：多平台歌词搜索、本地歌曲批量匹配、逐字歌词、LRC/SRT/ASS 等格式导出。不过本项目先从一个可扩展的命令行核心开始，后续可以在同一套核心能力上接桌面 UI。

## 当前能力

- 扫描本地音频文件并读取标题、歌手、专辑、时长等元数据
- 通过 LRCLIB 匹配同步歌词
- 解析、规范化、写出逐行 LRC
- 对候选歌词按元数据相似度和时长差异评分
- 预留 ASR 识别与歌词时间轴修正接口

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,asr]"
```

只安装基础歌词匹配能力：

```powershell
pip install -e .
```

查看本地歌曲元数据：

```powershell
lyrics-editor inspect "D:\Music\song.mp3"
```

在线搜索歌词：

```powershell
lyrics-editor search "D:\Music\song.mp3"
```

匹配并保存同名 `.lrc`：

```powershell
lyrics-editor match "D:\Music\song.mp3"
```

批量扫描目录：

```powershell
lyrics-editor scan "D:\Music" --save
```

用语音识别结果修正已有 LRC 时间轴：

```powershell
lyrics-editor repair "D:\Music\song.mp3" "D:\Music\song.lrc" --model-size medium
```

`repair` 命令会调用 `faster-whisper` 识别音频文本，再把识别片段和歌词行做单调匹配，输出 `song.repaired.lrc`。如果识别器返回逐字时间戳，内部会保留这些 `word timings`，后续可以继续扩展为逐字 LRC 或 ASS 卡拉 OK 样式。

## 路线图

1. 在线歌词源扩展：QQ 音乐、酷狗、网易云、手动候选选择。
2. 歌词格式扩展：增强型 LRC、逐字 LRC、SRT、ASS。
3. ASR 时间轴修正：从音频识别文本片段，和现有歌词做动态规划对齐，修正行级时间。
4. 逐字歌词：使用 ASR word timestamps 或平台逐字歌词，导出卡拉 OK 样式。
5. 桌面 UI：拖拽本地歌曲、候选歌词预览、时间轴编辑、批量写入标签。

## 项目结构

```text
src/lyrics_editor/
  audio.py              音频文件扫描与元数据读取
  cli.py                命令行入口
  lrc.py                LRC 解析和输出
  matcher.py            歌曲与候选歌词评分
  models.py             核心数据模型
  align/
    asr.py              ASR 识别接口和 faster-whisper 适配器
    text.py             文本规范化与对齐辅助
  providers/
    base.py             歌词源接口
    lrclib.py           LRCLIB 歌词源
```
