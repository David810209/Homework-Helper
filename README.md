# LineBot Project

這個branch應該是main，用來驅動LineBot的代碼（已經連接到Heroku）。

## 環境變數設置
所有的Key和Token都已經設置在Heroku的環境變數中。

## 安裝Heroku CLI
建議先下載Heroku CLI：
[Heroku CLI 安裝說明](https://devcenter.heroku.com/articles/heroku-cli#install-the-heroku-cli)
下載完成後，不需要做其他操作，就可以直接在終端運行指令。

## 修改專案方式
1. 切換到分支：
    ```sh
    git switch David
    ```

2. 修改完後提交變更：
    ```sh
    git add .
    git commit -m "修改說明"
    git push heroku David:main
    ```

這樣就會直接推送到Heroku，等待運行完成（可能需要一些時間）後，LineBot就會更新。如果推送完成後發現LineBot沒有反應，可以在終端輸入以下命令查看錯誤日誌：
```sh
heroku logs --tail
```

## 當前功能

- 可以通過聊天室直接與LineBot對話，但對話記錄功能尚未完成，只能進行單次對話。
- 可以直接詢問之前上傳的PDF檔案的內容（數值方法assignment1-4，密碼工程critique）。

### 上傳PDF檔案的方法

1. 先將PDF檔案上傳到Line Keep。
2. 從聊天室選擇Line Keep的圖標，然後將檔案傳給LineBot（只能使用電腦）。
3. 成功上傳後，LineBot會回應“上傳成功”。
4. 之後可以直接詢問已上傳檔案的問題。

