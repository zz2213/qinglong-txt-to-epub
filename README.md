### 青龙面板配置
- 1. config.sh配置
```env
# 基本配置
INPUT_DIR: (必填) TXT 目录。
OUTPUT_DIR: (必填) EPUB 目录。
TXT_FILE=./novels/novel.txt
COVER_DIR: (可选) 封面目录。
METADATA_FILE_PATH: (可选) 你上一步创建的 metadata.json 文件的绝对路径。例如：/ql/data/scripts/metadata.json。

# 章节检测配置
CHAPTER_DETECTION_METHOD=auto
ENABLE_DOUBLE_EMPTY_LINE=true

# 章节标记功能配置
ENABLE_CHAPTER_MARKER=false
CHAPTER_MARKER=#
```
## 🔍 章节检测策略

### Auto模式（默认）
- 优先使用特殊字符和模式匹配
- 如果启用双空行检测，作为兜底方案
- 如果启用章节标记功能，会在识别出的章节标题前添加特殊字符

### Pattern Only模式
- 仅使用特殊字符和模式匹配
- 不启用双空行检测

### Double Empty Line Only模式
- 仅使用双空行检测
- 适用于没有明确章节标记的文本
- 可以配合章节标记功能使用

## 🏷️ 章节标记功能详解

### 功能说明
当启用章节标记功能时，程序会在识别出章节标题后，自动在章节标题前添加指定的特殊字符。这个标记会出现在最终的EPUB文件中，使章节标题更加醒目。

### 使用场景
1. **统一章节格式**：将所有章节标题都标记为特殊字符格式
2. **提高可读性**：使章节标题在EPUB中更加醒目
3. **美化排版**：让章节标题具有统一的视觉样式


### ✨配置说明

| 配置项 | 说明         | 可选值 | 默认值                   |
|--------|------------|--------|-----------------------|
| `INPUT_DIR` | TXT文件路径    | 相对或绝对路径 | `./novels/`  |
| `OUTPUT_DIR` | Epub输出文件路径 | 相对或绝对路径 | `./novels/` |
| `COVER_DIR` | 封面图片路径     | 相对或绝对路径 | `./assets/`  |
| `CHAPTER_DETECTION_METHOD` | 章节检测方法     | `auto`, `pattern_only`, `double_empty_line_only` | `auto`                |
| `ENABLE_DOUBLE_EMPTY_LINE` | 是否启用双空行检测  | `true`, `false` | `true`                |
| `ENABLE_CHAPTER_MARKER` | 是否启用章节标记功能 | `true`, `false` | `false`               |
| `CHAPTER_MARKER` | 章节标记字符     | `#`, `##`, `@`, `*` 等 | `#`                   |
- 2. Bark推送配置
- 3. 青龙依赖python管理
     - requests
     - cn2an
     - EbookLib>=0.18
     - chardet>=5.0.0
     - httpx

### 脚本订阅

- 1.名称 (Name)：EPUB转换脚本

- 2. URL：https://github.com/zz2213/qinglong-txt-to-epub.git
    访问不了可以加上代理。示例：https://hk.gh-proxy.com/https://github.com/zz2213/qinglong-txt-to-epub.git

- 3. 拉取分支 (Branch)：填写 main 或者 master（取决于你 GitHub 仓库的默认分支名）。
- 4. 定时规则 (Schedule)：这个定时规则是用来**“检查并更新仓库”**的，而不是用来运行脚本的。
    推荐设置为一天一次，比如每天凌晨5点15分。
    示例：15 5 * * *
- 5.白名单 (Whitelist)：为了安全，只允许拉取 .py 文件。填写：.*\.py$



### 配置示例
```
# 启用章节标记功能，使用 # 作为标记
ENABLE_CHAPTER_MARKER=true
CHAPTER_MARKER=#

# 启用章节标记功能，使用 ## 作为标记
```


### 依赖库
- **EbookLib**: EPUB文件生成
- **chardet**: 文本编码检测