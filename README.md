# pokerServer

## 概述
本專案是一個 **撲克遊戲伺服器**，使用 Python **socket** 模組建立多人連線，讓玩家透過 **TCP 通訊** 進行撲克遊戲。伺服器負責管理玩家的登入、遊戲狀態同步、下注邏輯以及比牌決定勝負。

## 主要功能
- **玩家管理**
  - 玩家登入/註冊
  - 更新玩家籌碼與狀態
  - 處理玩家離線
- **遊戲邏輯**
  - 控制遊戲回合 (Flop, Turn, River)
  - 計算底池金額 (Pot)
  - 進行下注、跟注、加注、全押 (Bet, Call, Raise, All-in)
- **通訊處理**
  - 傳遞遊戲狀態給所有玩家
  - 確保多人連線的同步性
  - 傳送遊戲結束資訊

## 安裝與運行

### 1. 安裝 Python 依賴
```sh
pip install json
```

### 2. 啟動伺服器
```sh
python server.py
```
預設 **監聽 `0.0.0.0:8888`**，最多 6 名玩家。

### 3. 停止伺服器
在伺服器終端輸入：`CTRL + C`。

## 目錄結構
```
poker-server/
├── server.py                 # 撲克伺服器主程式
├── card.py                   # 撲克牌邏輯處理
├── user.json                 # 使用者帳戶資訊
├── players_information.json   # 遊戲內玩家資訊
├── poker.json                # 卡牌資訊
├── README.md                 # 說明文件
```
