# check-16kb

Google Play refuses an app that targets Android 15 or later when its native libraries are not 16 KB aligned. This script builds each app's release APK (arm64-v8a and x86_64), checks the zip alignment with `zipalign -P 16`, and reads the ELF LOAD alignment of every `.so` with `llvm-objdump`. It exits 1 if any app fails.

## Install

    ./install.sh check-16kb    # copies check-16kb to ~/.claude/bin

## Usage

    APPS_DIR=~/work check-16kb app1 app2

Each argument is a folder under `APPS_DIR` (default: the current folder) with a Gradle project in `android/` and the `:app:assembleRelease` task. Run one app at a time: a build takes 5 to 15 minutes, and over two hours on a loaded machine.

- `ANDROID_HOME` names the SDK. Without it the script reads `sdk.dir` from the first app's `android/local.properties`.
- The SDK needs `build-tools` and an NDK (for `llvm-objdump`); the newest of each is used.
- An app without `android/release-signing.properties` is signed with a throwaway key made in a temp folder, and the properties file is removed afterwards. An existing file is used as it is and never touched.
- The properties file must hold `storeFile`, `storePassword`, `keyAlias` and `keyPassword`, and the app's Gradle config must read it.
- The build passes `-PreactNativeArchitectures=arm64-v8a,x86_64`, which only React Native projects use.

No self-test: it runs a real build.

## Requirements

zsh, a JDK (`keytool`), the Android SDK build-tools and NDK, unzip.
