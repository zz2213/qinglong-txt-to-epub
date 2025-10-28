## 青龙脚本 txt转epub

- 1. 扫描对应目录下文件与文件夹 文件夹下所有文件合并成一个文件
- 2. 处理更新的文件重新转化
- 3. 转化成功使用青龙面板Bark通知
 

### 青龙面板配置
- 1. config.sh配置
```ymal
# ========= TXT转EPUB脚本自定义配置 =========
export TXT_SOURCE_FOLDER="/ql/data/my_txts/" #扫描文件目录
export EPUB_DEST_FOLDER="/ql/all/" #生成epub文件目录
```
- 2. 青龙依赖python管理
     - requests
     - cn2an
     - EbookLib==0.17.1
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



