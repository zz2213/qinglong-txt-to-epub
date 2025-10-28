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
