# External Tool Requirements

LogGuardian relies on Gitleaks and TruffleHog to generate secret candidates. Because the executable files are large and belong to third-party software, they are not included in 
this repository. Please download the appropriate versions for your operating system from their official release pages.

The versions used in this study were:

- Gitleaks v8.29.0
- TruffleHog v3.91.0

Official release pages:

- Gitleaks: https://github.com/gitleaks/gitleaks/releases
- TruffleHog: https://github.com/trufflesecurity/trufflehog/releases

After downloading and extracting the tools, place the Windows executable files in the current `tool` directory and ensure that they have the following names:

```text
code/tool/gitleaks.exe
code/tool/trufflehog.exe
