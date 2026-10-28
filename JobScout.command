#!/bin/zsh
cd "${0:A:h}"
for python_path in /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if [[ -x "$python_path" ]] && "$python_path" -c 'import sys; assert sys.version_info >= (3,11)' 2>/dev/null; then
    if "$python_path" start_service.py; then
      /usr/bin/open http://127.0.0.1:8765
      exit 0
    fi
    break
  fi
done
print 'JobScout 启动失败。请保留此窗口中的错误信息。'
read -k 1 '?按任意键关闭…'
