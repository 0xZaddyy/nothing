@echo off
start "" "%ProgramFiles%\Git\git-bash.exe" -c "cd /c/dev/vercel && vercel dev"

start "" "%ProgramFiles%\Git\git-bash.exe" --login -i -c ^
"cd /c/dev/mariokart; while true; do echo ''; echo '🎮 Starting game...'; python mario.py || echo 'Exited with error'; echo ''; echo '🔁 Restarting in 1s... Ctrl+C again to quit'; sleep 1; done"
start "" "%ProgramFiles%\Git\git-bash.exe" -c "cd /c/dev/mariokart && python mario.py"

start "" "mario.ahk"

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --start-fullscreen http://localhost:5000