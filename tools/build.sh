#!/usr/bin/env bash
# Builds the signed Android app from android/ plus the current docs/app.html.
# Usage: tools/build.sh            -> dist/watchlist.apk
# Needs Java. Downloads Apktool 2.10.0 and uber-apk-signer 1.3.0 from GitHub into $TOOLS_DIR the first time.
set -euo pipefail
cd "$(dirname "$0")/.."
TOOLS_DIR=${TOOLS_DIR:-/tmp/watchlist-tools}
mkdir -p "$TOOLS_DIR" dist
[ -s "$TOOLS_DIR/apktool.jar" ] || curl -fsSL -o "$TOOLS_DIR/apktool.jar" https://github.com/iBotPeaches/Apktool/releases/download/v2.10.0/apktool_2.10.0.jar
[ -s "$TOOLS_DIR/signer.jar" ] || curl -fsSL -o "$TOOLS_DIR/signer.jar" https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar

# The bundled page and the starter page must agree on the build number.
page_build=$(grep -oE 'const BUILD = [0-9]+' docs/app.html | grep -oE '[0-9]+')
loader_build=$(grep -oE 'var BUNDLED = [0-9]+' android/assets/index.html | grep -oE '[0-9]+')
if [ "$page_build" != "$loader_build" ]; then
  echo "BUILD in docs/app.html ($page_build) != BUNDLED in android/assets/index.html ($loader_build)" >&2; exit 1
fi
cp docs/app.html android/assets/app.html

rm -rf android/build dist/unsigned.apk dist/signed
java -jar "$TOOLS_DIR/apktool.jar" b android -o dist/unsigned.apk
java -jar "$TOOLS_DIR/signer.jar" --apks dist/unsigned.apk --out dist/signed \
  --ks android/signing/debug.keystore --ksAlias androiddebugkey --ksPass android --ksKeyPass android
signed=$(ls dist/signed/*.apk)

# Same key as every earlier version, or Android refuses to install over the old app.
want="1e08a903aef9c3a721510b64ec764d01d3d094eb954161b62544ea8f187b5953"
got=$(java -jar "$TOOLS_DIR/signer.jar" --onlyVerify --apks "$signed" | grep -oiE 'SHA256: [0-9a-f]{64}' | head -1 | awk '{print tolower($2)}')
if [ "$got" != "$want" ]; then echo "Signing key changed ($got). Do not ship." >&2; exit 1; fi
mv "$signed" dist/watchlist.apk
rm -rf dist/signed dist/unsigned.apk android/build
echo "Built dist/watchlist.apk (page build $page_build)"
