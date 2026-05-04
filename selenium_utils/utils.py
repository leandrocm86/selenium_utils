from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, TypeVar

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as WDWait

if TYPE_CHECKING:
    from .driver import SeleniumDriver
    from .element import SeleniumElement

# Drivers alternativos em https://sites.google.com/chromium.org/driver/
# Instalados com snap install chromium no ubuntu (chromium é só via snap agora)
DEFAULT_BIN_PATH = "/usr/bin/chromium"
SNAP_BIN_PATH = "/snap/bin/chromium"

T = TypeVar("T")


def remove_tags(text: str):
    while True:
        index_tag_start = text.find("<")
        index_tag_end = text.find(">", index_tag_start)
        if index_tag_start == -1 or index_tag_end == -1:
            break
        text = text[:index_tag_start] + text[index_tag_end + 1 :]
    return text


def wait_for(
    parent: SeleniumElement | SeleniumDriver, selector: str, by: str = By.CSS_SELECTOR, timeout: int = 10
) -> list[SeleniumElement]:
    from .element import SeleniumElement

    # In original code:
    # driver = parent.driver if isinstance(parent, SeleniumElement) else parent
    # but I can't use isinstance without importing.

    if hasattr(parent, "webelement"): # It's a SeleniumElement
        selenium_driver = parent.driver
    else: # It's a SeleniumDriver
        selenium_driver = parent

    try:
        def search():
            if hasattr(parent, "webelement"):
                found_elems = parent.webelement.find_elements(by, selector)
            else:
                found_elems = parent.raw_driver.find_elements(by, selector)
            selenium_driver.logfunc(f"Found {len(found_elems)} elements searching for {selector}")
            return [SeleniumElement(e, selenium_driver) for e in found_elems]

        return WDWait(selenium_driver.raw_driver, poll_frequency=1, timeout=timeout).until(lambda _: search())
    except TimeoutException:
        selenium_driver.logfunc("Timeout reached while searching for " + selector)
        return []


def extract_diagnostics():
    diagnostics = {}

    # 1. Memória do CONTAINER
    try:
        # cgroup v2 (padrão atual)
        if os.path.exists("/sys/fs/cgroup/memory.current"):
            usage = int(subprocess.check_output("cat /sys/fs/cgroup/memory.current", shell=True, text=True).strip())
            limit = subprocess.check_output("cat /sys/fs/cgroup/memory.max", shell=True, text=True).strip()
            limit = int(limit) if limit != "max" else "ilimitado"

            if isinstance(limit, int):
                available = limit - usage
                diagnostics["memory_container"] = f"Uso: {usage//1024//1024} MB | Limite: {limit//1024//1024} MB | Disponível: {available//1024//1024} MB"
            else:
                diagnostics["memory_container"] = f"Uso: {usage//1024//1024} MB | Limite: ilimitado"
        # fallback cgroup v1 (imagens antigas)
        elif os.path.exists("/sys/fs/cgroup/memory/memory.usage_in_bytes"):
            usage = int(subprocess.check_output("cat /sys/fs/cgroup/memory/memory.usage_in_bytes", shell=True, text=True).strip())
            limit = int(subprocess.check_output("cat /sys/fs/cgroup/memory/memory.limit_in_bytes", shell=True, text=True).strip())
            available = limit - usage
            diagnostics["memory_container"] = f"Uso: {usage//1024//1024} MB | Limite: {limit//1024//1024} MB | Disponível: {available//1024//1024} MB"
        else:
            diagnostics["memory_container"] = "Cgroup não encontrado"
    except Exception as e:
        diagnostics["memory_container"] = f"Erro ao ler cgroup: {e}"

    # 2. /dev/shm (mesmo com --disable-dev-shm-usage, vale conferir)
    try:
        diagnostics["shm"] = subprocess.check_output("df -h /dev/shm", shell=True, text=True)
    except:
        diagnostics["shm"] = "Não foi possível ler /dev/shm"

    # 3. Quantidade de PIDs atuais + limite do container (cgroup v1 e v2)
    try:
        current_pids = subprocess.check_output("ps -eo pid --no-headers | wc -l", shell=True, text=True).strip()
        diagnostics["pids_current"] = current_pids

        # cgroup v1 e v2 (funciona na maioria das imagens selenium)
        for cgroup in ["v1", "v2"]:
            if cgroup == "v1":
                limit_cmd = "cat /sys/fs/cgroup/pids/pids.max 2>/dev/null || echo 'N/A'"
                usage_cmd = "cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null && cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo 'N/A'"
            else:
                limit_cmd = "cat /sys/fs/cgroup/pids.max 2>/dev/null || echo 'N/A'"
                usage_cmd = "cat /sys/fs/cgroup/memory.current 2>/dev/null && cat /sys/fs/cgroup/memory.max 2>/dev/null || echo 'N/A'"

            diagnostics[f"pids_limit_{cgroup}"] = subprocess.check_output(limit_cmd, shell=True, text=True).strip()
            diagnostics[f"memory_cgroup_{cgroup}"] = subprocess.check_output(usage_cmd, shell=True, text=True).strip()
    except:
        diagnostics["pids"] = "Não foi possível ler PIDs"

    # 4. /tmp (não pode ser pequeno!)
    try:
        diagnostics["tmp_mount"] = subprocess.check_output("findmnt -T /tmp -o SOURCE,TARGET,FSTYPE,OPTIONS", shell=True, text=True).strip()
        diagnostics["tmp_df"] = subprocess.check_output("df -h /tmp", shell=True, text=True).strip()
        diagnostics["tmp_ls"] = subprocess.check_output("ls -ld /tmp", shell=True, text=True).strip()
    except Exception as e:
        diagnostics["tmp_info"] = f"Erro ao ler /tmp: {e}"

    # 5. Últimas linhas do log do Chrome (se habilitado)
    try:
        with open("/tmp/custom_profile/chrome_debug.log", "r", encoding="utf-8", errors="ignore") as f:
            diagnostics["chrome_log"] = "".join(f.readlines()[-30:])
    except:
        diagnostics["chrome_log"] = "Log do Chrome não encontrado"

    # Exibe tudo de forma organizada
    diagtext = "\n" + "="*60 + "DIAGNÓSTICO DO CRASH\n" + "="*60
    for key, value in diagnostics.items():
        diagtext += f"\n🔹 {key.upper()}: {value.strip()}"
    diagtext += "\n="*60
    
    return diagtext
