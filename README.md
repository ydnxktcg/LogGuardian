# LogGuardian

LogGuardian is a sensitive-information detection tool for CI/CD build logs. It combines Gitleaks, TruffleHog, custom regular expressions, and a context-aware machine learning model to extract candidate secrets from logs and distinguish true secrets from benign values.

## 📁 Project Structure

After the required tools have been configured, the project structure should be as follows:

```text
LogGuardian/
├── code/
│   ├── model/
│   │   ├── classifier.pkl
│   │   └── graphcodebert-base/   # Download as needed
│   ├── src/
│   │   ├── aggregator/
│   │   ├── inference/
│   │   └── scanner/
│   ├── tool/                     # Created by the user
│   │   ├── gitleaks.exe
│   │   └── trufflehog.exe
│   ├── data/                     # Created only for model retraining
│   │   ├── Train.json            # Split prepared by the user
│   │   ├── Val.json              # Split prepared by the user
│   │   └── Test.json             # Split prepared by the user
│   ├── detect.py
│   ├── train.py
│   └── requirements.txt
├── docs/
└── README.md
```

GitHub does not preserve empty directories. Therefore, the `tool/` and `data/` directories are not included by default and should be created when needed.

## ⚙️ Environment and Installation

Python 3.12 is recommended. This project has been tested with Python 3.12.6.

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

If no compatible GPU is available, the program automatically uses the CPU.

## 🧠 GraphCodeBERT Model

The repository already includes the trained classifier at `code/model/classifier.pkl`; users do not need to retrain the model. LogGuardian also requires the GraphCodeBERT backbone. Choose either of the following methods.

**Online loading:** If GraphCodeBERT is not available locally, the program automatically downloads `microsoft/graphcodebert-base` from Hugging Face. An Internet connection is required on the first run.

**Offline loading:** If Hugging Face is inaccessible, download the model files from the project's Model Release:

- Release page: https://github.com/ydnxktcg/LogGuardian/releases/tag/model
- Direct download: https://github.com/ydnxktcg/LogGuardian/releases/download/model/graphcodebert-base.zip

After downloading and extracting the archive, place the entire `graphcodebert-base` directory at:

```text
code/model/graphcodebert-base/
```

The final structure should be:

```text
code/model/
├── classifier.pkl
└── graphcodebert-base/
    ├── config.json
    ├── merges.txt
    ├── pytorch_model.bin
    ├── special_tokens_map.json
    ├── tokenizer_config.json
    └── vocab.json
```

The program prioritizes the local model and attempts to download from Hugging Face only when the local model is absent.

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

Download the dataset from the GitHub Release:

- Release page: https://github.com/ydnxktcg/LogGuardian/releases/tag/dataset
- Direct download: https://github.com/ydnxktcg/LogGuardian/releases/download/dataset/dataset.zip

The repository already includes the trained `code/model/classifier.pkl`; therefore, the `data` directory is not required when using LogGuardian only for detection.

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

## 🛠️ Troubleshooting

### 1. NumPy conflict in the Anaconda `(base)` environment

If the error contains:

```text
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x
```

NumPy in the current Anaconda `base` environment is incompatible with binary dependencies such as Pandas, PyArrow, or Scikit-learn. Instead of modifying the `base` environment, use an isolated environment.

If Python 3.12 is already installed:

```powershell
conda deactivate
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If only Anaconda or Miniconda is available, create an isolated Conda environment:

```powershell
conda create -n logguardian python=3.12 -y
conda activate logguardian
python -m pip install -r requirements.txt
```

After activation, the terminal prompt should begin with `(.venv)` or `(logguardian)`, rather than `(base)`.

### 2. Unable to activate `.venv`

If PowerShell cannot find:

```text
.\.venv\Scripts\Activate.ps1
```

the virtual environment was not created successfully. First check whether Python is available:

```powershell
python --version
```

Then create and activate the environment again:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, temporarily allow scripts for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### 3. Unable to connect to Hugging Face

If the program repeatedly retries or reports a connection failure while loading `microsoft/graphcodebert-base`, model retraining is not required. Download the offline model from the Model Release:

https://github.com/ydnxktcg/LogGuardian/releases/tag/model

After extraction, ensure that the directory is located at:

```text
code/model/graphcodebert-base/
```

The program automatically prioritizes this local directory.

### 4. The program exits immediately

Confirm that the following files exist:

```text
code/model/classifier.pkl
code/tool/gitleaks.exe
code/tool/trufflehog.exe
```

Run the following commands from the `code` directory:

```powershell
Test-Path .\model\classifier.pkl
Test-Path .\tool\gitleaks.exe
Test-Path .\tool\trufflehog.exe
```

All three commands should return `True`.

## ⚠️ Notes

- Scan only logs and directories that you are authorized to process.
- Detection results may contain sensitive information. Store them securely and do not commit them to a public repository.
- Gitleaks and TruffleHog are independent third-party projects. Their respective copyrights and licenses remain with their original projects.
