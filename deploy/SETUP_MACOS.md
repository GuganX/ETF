# 在另一台 Mac 上部署「每天自動抓取 + 推送」

整個流程一次做完,之後那台機器每天會自動:抓持股 → 更新 `index.html` → push 到 GitHub。
以下指令直接在**那台新 Mac** 的「終端機」貼上執行。

---

## 0. 先裝基本工具(Homebrew + git + python)

```bash
# 安裝 Homebrew(若已有可略過)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 git 與 python
brew install git python
```

---

## 1. 產生這台機器專屬的 SSH 金鑰,並加到 GitHub

每台機器用自己的金鑰最乾淨(這台壞了直接在 GitHub 撤銷即可)。

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_personal -N "" -C "etf-bot-$(hostname)"
cat ~/.ssh/id_ed25519_personal.pub        # 複製這一行
```

把印出的公鑰貼到:GitHub(GuganX 帳號)→ Settings → SSH and GPG keys → New SSH key。

設定 SSH 用這把金鑰連 github.com:

```bash
cat >> ~/.ssh/config <<'EOF'

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_personal
    IdentitiesOnly yes
EOF

ssh -T -o StrictHostKeyChecking=accept-new git@github.com   # 應看到 "Hi GuganX!"
```

---

## 2. 設定 git 個人署名(這台機器是個人用,直接設全域)

```bash
git config --global user.name  "GuganX"
git config --global user.email "cklrdg@gmail.com"
```

---

## 3. Clone 專案並安裝 Python 環境

```bash
mkdir -p ~/personal && cd ~/personal
git clone git@github.com:GuganX/ETF.git etf
cd ~/personal/etf
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

先手動跑一次,確認抓取 / 產報表 / push 都正常:

```bash
./run_daily.sh
cat fetch.log        # 看結果
```

---

## 4. 掛上 launchd 排程(每天 18:00 / 20:00 / 22:00 自動跑)

直接貼以下整段,它會用「這台機器的實際家目錄路徑」產生排程檔並啟用:

```bash
PLIST="$HOME/Library/LaunchAgents/com.guganx.etf-daily.plist"
REPO="$HOME/personal/etf"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.guganx.etf-daily</string>
    <key>ProgramArguments</key>
    <array><string>$REPO/run_daily.sh</string></array>
    <key>WorkingDirectory</key><string>$REPO</string>
    <key>EnvironmentVariables</key>
    <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key><string>$REPO/launchd.log</string>
    <key>StandardErrorPath</key><string>$REPO/launchd.log</string>
</dict>
</plist>
EOF

# 載入並啟用
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST"
echo "已啟用,排程清單:"
launchctl list | grep etf-daily
```

---

## 5. 驗證 / 常用指令

```bash
# 馬上手動觸發一次排程(不等到 18:00)
launchctl start com.guganx.etf-daily
cat ~/personal/etf/launchd.log

# 之後想停用排程
launchctl unload ~/Library/LaunchAgents/com.guganx.etf-daily.plist

# 想改時間 → 編輯上面的 plist 後,再 unload 一次、load 一次
```

---

## 注意事項

- **機器要開著**:launchd 在 Mac 睡眠時不會跑,但醒來後會補跑當天錯過的排程;若要 24h 不漏,讓那台 Mac 不要睡眠(系統設定 → 螢幕鎖定/節能 設為不睡眠)。
- **金鑰無密碼**:第 1 步產的金鑰沒設 passphrase,launchd 才能非互動 push。這台機器請當作專用自動化機,妥善保管。
- **資料庫不上傳**:`etf_holdings.db` 在 `.gitignore` 內,只存在那台機器本機;push 上 GitHub 的只有 `index.html`。
- **看線上報表**:開啟 GitHub Pages 後,網址是 `https://guganx.github.io/ETF/`。
