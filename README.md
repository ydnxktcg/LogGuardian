# LogGuardian

LogGuardian is a sensitive-information detection tool for CI/CD build logs. It combines Gitleaks, TruffleHog, custom regular expressions, and a context-aware machine learning model to extract candidate secrets from logs and distinguish true secrets from benign values.

## 📁 Project Structure

After the required tools have been configured, the project structure should be as follows:

```text
LogGuardian/
├── code/
│   ├── model/
│   │   └── classifier.pkl
│   ├── src/
│   │   ├── aggregator/
│   │   ├── inference/
│   │   └── scanner/
│   ├── tool/                  # Created by the user
│   │   ├── gitleaks.exe
│   │   └── trufflehog.exe
│   ├── data/                  # Required only for model retraining
│   │   ├── Train.json         # Prepared by the user
│   │   ├── Val.json           # Prepared by the user
│   │   └── Test.json          # Prepared by the user
│   ├── detect.py
│   ├── train.py
│   └── requirements.txt
├── docs/
└── README.md
```

GitHub does not preserve empty directories. Therefore, the `tool/` and `data/` directories are not included by default and should be created when needed.

## ⚙️ Environment and Installation

Python 3.12 is recommended. The project has been tested with Python 3.12.6.

```bash
git clone https://github.com/ydnxktcg/LogGuardian.git
cd LogGuardian/code
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On the first run, the program automatically downloads `microsoft/graphcodebert-base`, so an Internet connection is required. If no compatible GPU is available, the program automatically uses the CPU.

## 🔧 External Scanning Tools

LogGuardian depends on Gitleaks and TruffleHog. Because their executable files are large and belong to third-party software, they are not distributed with this repository.

The versions used in this study were:

- Gitleaks v8.29.0: https://github.com/gitleaks/gitleaks/releases
- TruffleHog v3.91.0: https://github.com/trufflesecurity/trufflehog/releases

After downloading and extracting the tools, create a `tool` directory under `code`, place both executable files in it, and ensure that their paths and filenames are:

```text
code/tool/gitleaks.exe
code/tool/trufflehog.exe
```

## 🚀 Usage

Run all commands from the `code` directory.

Scan a single file:

```bash
python detect.py -p "C:\path\to\build.log"
```

Recursively scan a directory:

```bash
python detect.py -p "C:\path\to\logs"
```

Save the results to a JSON file:

```bash
python detect.py -p "C:\path\to\logs" -o "C:\path\to\result.json"
```

The `-p` (or `--path`) argument specifies the file or directory to scan. The `-o` (or `--output`) argument is optional. If `-o` is omitted, the results are printed directly to the console.

## 📦 Dataset and Model Training

The dataset is available from the GitHub Release:

- Release page: https://github.com/ydnxktcg/LogGuardian/releases/tag/dataset
- Direct download: https://github.com/ydnxktcg/LogGuardian/releases/download/dataset/dataset.zip

The repository already includes the trained classifier at `code/model/classifier.pkl`. Therefore, the `data` directory is not required when using LogGuardian only for detection.

To retrain the model, create a `data` directory under `code`, split the downloaded dataset into training, validation, and test sets, and use the following filenames:

```text
code/data/Train.json
code/data/Val.json
code/data/Test.json
```

After preparing the data, run the following command from the `code` directory:

```bash
python train.py
```

The default random seed is `42`. A different seed can be specified with the `--seed` argument, for example:

```bash
python train.py --seed 123
```

## ⚠️ Notes

- Scan only logs and directories that you are authorized to process.
- Detection results may contain sensitive information. Store them securely and do not commit them to a public repository.
- Gitleaks and TruffleHog are independent third-party projects. Their respective copyrights and licenses remain with their original projects.

