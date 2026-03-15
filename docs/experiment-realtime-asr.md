# 实验：实时显示语音识别文字

## 目标

在录音过程中实时显示识别出的文字，而不是等到录音结束后再显示。

## 技术方案

### 整体思路

```
录音线程 ──┬──> 临时文件 ──> 识别线程 ──> GUI 实时更新
           │
           └──> 每隔 N 秒读取已录制部分 ──> 增量识别 ──> 实时显示
```

### 实现步骤

1. **录音同时启动识别线程**
   - 使用 `faster-whisper` 定期读取已录制音频
   - 每 2-3 秒做一次增量识别

2. **GUI 接收实时更新**
   - `app.py` 中添加回调机制
   - 识别到新内容就推送到 GUI 显示

3. **线程同步**
   - 录音写文件 vs 识别读文件需要加锁
   - 或使用独立的临时文件

### 复杂度评估

- 约 80-150 行新代码
- 主要在 `app.py` 和 `recorder.py` 修改
- 难度：中等（主要是线程协调）

---

## Git 分支实验流程

### 1. 创建实验分支

```bash
# 从 master 创建并切换到新分支
git checkout -b experiment-realtime-asr
```

### 2. 在分支上开发

所有修改都在 `experiment-realtime-asr` 分支上进行，与 master 完全隔离。

### 3. 实验结果

**成功 → 合并回 master**

```bash
# 切换回 master
git checkout master

# 合并实验分支
git merge experiment-realtime-asr

# 删除实验分支
git branch -d experiment-realtime-asr
```

**失败 → 放弃实验分支**

```bash
# 切换回 master
git checkout master

# 强制删除实验分支（代码恢复原状）
git branch -D experiment-realtime-asr
```

---

## 当前状态

- **主分支**: master
- **功能状态**: 录音完成后才显示文字
- **目标状态**: 录音过程中实时显示文字
