# Lyrics Editor

本项目用于处理本地音乐文件：读取元数据、匹配在线歌词、保存 LRC，并为后续的 ASR 时间轴修正和逐字歌词打基础。

参考了 [LDDC](https://github.com/chenmozhijin/LDDC) 的方向，但先从一个可扩展的本地核心开始，再逐步接桌面界面。

## 当前能力

- 扫描本地音频文件并读取标题、歌手、专辑、时长
- 匹配歌词来源：LRCLIB、lyrics.ovh、同目录 sidecar `.lrc` / `.txt`
- 解析、规范化、写出逐行 LRC
- 按元数据相似度和时长差异给候选歌词打分
- 用 ASR 结果修正 LRC 时间轴
- 打开桌面界面浏览歌曲、切换来源、预览候选并保存歌词

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,asr]"
```

基础安装：

```powershell
pip install -e .
```

查看元数据：

```powershell
lyrics-editor inspect "D:\Music\song.mp3"
```

搜索歌词：

```powershell
lyrics-editor search "D:\Music\song.mp3"
```

如果文件标签不准，可以手动覆盖标题、歌手或专辑：

```powershell
lyrics-editor search "D:\Music\song.mp3" --title "歌曲名" --artist "歌手名"
```

手动选择候选：

```powershell
lyrics-editor choose "D:\Music\song.mp3"
```

自动匹配并保存：

```powershell
lyrics-editor match "D:\Music\song.mp3"
```

批量扫描：

```powershell
lyrics-editor scan "D:\Music" --save
```

修正时间轴：

```powershell
lyrics-editor repair "D:\Music\song.mp3" "D:\Music\song.lrc"
```

打开桌面界面：

```powershell
lyrics-editor gui
```

也可以直接运行：

```powershell
lyrics-editor-gui
```

在桌面界面里，右侧“搜索信息”可以直接改标题、歌手、专辑，再点“搜索”或“保存最佳”。这对标签不完整的歌曲特别有用。

## 路线图

1. 继续扩展歌词源，加入 QQ 音乐、网易云、酷狗等。
2. 增强逐字歌词和卡拉 OK 导出。
3. 改进 ASR 与歌词的对齐算法。
4. 继续完善桌面界面的批量操作与拖拽体验。
