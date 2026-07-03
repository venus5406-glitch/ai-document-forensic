import { accessSync, constants } from "node:fs";
import { join } from "node:path";
import { spawn, spawnSync } from "node:child_process";

const root = process.cwd();
const isWindows = process.platform === "win32";
const appFile = join(root, "app.py");
const requirementsFile = join(root, "requirements.txt");
const port = process.env.PORT || "8501";
const streamlitArgs = [
  "run",
  appFile,
  "--server.address",
  "localhost",
  "--server.port",
  port,
];

main();

function main() {
  const streamlit = findExecutable([
    join(root, ".venv", isWindows ? "Scripts/streamlit.exe" : "bin/streamlit"),
    join(root, "venv", isWindows ? "Scripts/streamlit.exe" : "bin/streamlit"),
    isWindows ? "streamlit.exe" : "streamlit",
    isWindows ? "streamlit.cmd" : "streamlit",
  ]);

  if (streamlit) {
    start(streamlit.command, streamlitArgs);
    return;
  }

  const python = findPython();
  if (!python) {
    printPythonInstallHelp();
    process.exit(1);
  }

  ensureStreamlit(python);
  start(python.command, ["-m", "streamlit", ...streamlitArgs]);
}

function findPython() {
  const candidates = [
    join(root, ".venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    join(root, "venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    isWindows ? "py.exe" : "python3",
    isWindows ? "python.exe" : "python",
    "python",
  ];

  return findExecutable(candidates, {
    rejectWindowsStoreAlias: true,
    validate: (command) => run(command, ["--version"], { stdio: "ignore" }).status === 0,
  });
}

function findExecutable(candidates, options = {}) {
  for (const candidate of candidates) {
    const resolved = resolveExecutable(candidate, options);
    if (!resolved) {
      continue;
    }

    const command = resolved;
    const validationOk = options.validate
      ? options.validate(command)
      : run(command, ["--version"], { stdio: "ignore" }).status === 0;

    if (validationOk) {
      return { command };
    }
  }
  return null;
}

function resolveExecutable(command, options = {}) {
  if (command.includes("/") || command.includes("\\")) {
    try {
      accessSync(command, constants.X_OK);
      return command;
    } catch {
      return null;
    }
  }

  if (!isWindows) {
    const result = spawnSync("command", ["-v", command], { shell: true, encoding: "utf8" });
    return result.status === 0 ? command : null;
  }

  const result = spawnSync("where.exe", [command], { encoding: "utf8" });
  if (result.status !== 0) {
    return null;
  }

  const matches = result.stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  for (const match of matches) {
    if (options.rejectWindowsStoreAlias && match.toLowerCase().includes("\\windowsapps\\")) {
      continue;
    }
    return match;
  }
  return null;
}

function ensureStreamlit(python) {
  const importCheck = run(python.command, ["-c", "import streamlit"], { stdio: "ignore" });
  if (importCheck.status === 0) {
    return;
  }

  console.log("Streamlit 의존성이 없어 requirements.txt를 설치합니다...");
  const install = run(python.command, ["-m", "pip", "install", "-r", requirementsFile], {
    stdio: "inherit",
  });

  if (install.status !== 0) {
    console.error("");
    console.error("Python은 찾았지만 의존성 설치에 실패했습니다.");
    console.error("아래 명령을 직접 실행한 뒤 다시 시도하세요:");
    console.error(`  ${python.command} -m pip install -r requirements.txt`);
    console.error("  npm run dev");
    process.exit(install.status ?? 1);
  }
}

function start(command, args) {
  console.log(`DocuGuard AI 개발 서버를 시작합니다: http://localhost:${port}`);
  const child = spawn(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: false,
  });

  child.on("error", (error) => {
    console.error(`실행 실패: ${error.message}`);
    process.exit(1);
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}

function run(command, args, options = {}) {
  if (isWindows && command.endsWith(".cmd")) {
    return spawnSync("cmd.exe", ["/d", "/s", "/c", command, ...args], {
      cwd: root,
      ...options,
    });
  }

  return spawnSync(command, args, {
    cwd: root,
    ...options,
  });
}

function printPythonInstallHelp() {
  console.error("");
  console.error("실제 Python 실행 파일을 찾지 못했습니다.");
  console.error("현재 Windows의 Microsoft Store Python 실행 별칭만 잡힌 상태일 가능성이 큽니다.");
  console.error("");
  console.error("해결 방법:");
  console.error("  1. Python 3.11 이상을 설치하세요: https://www.python.org/downloads/");
  console.error("  2. 설치 화면에서 Add python.exe to PATH를 체크하세요.");
  console.error("  3. 새 터미널을 열고 다시 실행하세요:");
  console.error("     npm run dev");
  console.error("");
  console.error("winget을 쓸 수 있다면 다음 명령으로도 설치할 수 있습니다:");
  console.error("  winget install Python.Python.3.12");
}
