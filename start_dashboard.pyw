"""
Dashboard'u arka planda başlatır.
.pyw uzantısı sayesinde konsol penceresi açılmaz.
Görev Zamanlayıcı veya Windows başlangıcında çalıştırılabilir.
"""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
subprocess.Popen(
    [sys.executable, os.path.join(BASE, "dashboard", "app.py")],
    cwd=BASE,
    creationflags=0x00000008,  # DETACHED_PROCESS — parent ölünce yaşamaya devam eder
)
