#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔥 Starting dependency installation..."

# Detect OS Type
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ Unable to determine OS."
    exit 1
fi

# Function to install a package if it's not already installed
install_package() {
    PACKAGE_NAME=$1
    if ! command -v "$PACKAGE_NAME" &> /dev/null; then
        echo "🔧 Installing $PACKAGE_NAME..."
        if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
            apt-get update && apt-get install -y "$PACKAGE_NAME"
        elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "amzn" ]]; then
            yum install -y "$PACKAGE_NAME"
        elif [[ "$OS" == "alpine" ]]; then
            apk add --no-cache "$PACKAGE_NAME"
        else
            echo "⚠️ OS not supported for automatic installation of $PACKAGE_NAME."
        fi
    else
        echo "✅ $PACKAGE_NAME is already installed."
    fi
}

# Install Core Dependencies
install_package "curl"
install_package "wget"
install_package "unzip"
install_package "git"
install_package "bash"

# Install Build Tools
install_package "maven"
install_package "gradle"
install_package "golang"
install_package "ant"

# Install Node.js, npm, and Yarn
echo "📦 Installing Node.js, npm, and Yarn..."
install_package "nodejs"
install_package "npm"
npm install -g yarn
echo "✅ Node.js, npm, and Yarn installed."

# Install Docker
install_package "docker.io"


# Install SonarQube CLI
echo "📊 Installing SonarQube CLI..."
SONAR_VERSION="4.7.0.2747"
if [ ! -d "/opt/sonar-scanner-${SONAR_VERSION}-linux" ]; then
    wget -q https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_VERSION}-linux.zip -O /tmp/sonar-scanner.zip
    unzip -o /tmp/sonar-scanner.zip -d /opt/
    mv /opt/sonar-scanner-${SONAR_VERSION}-linux /opt/sonar-scanner
    ln -sf /opt/sonar-scanner/bin/sonar-scanner /usr/local/bin/sonar-scanner
    echo "✅ SonarQube CLI installed."
else
    echo "✅ SonarQube CLI is already installed."
fi

# Install Trivy
echo "🔍 Installing Trivy..."
apt-get install -y gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/trivy-archive-keyring.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/trivy.list
apt-get update && apt-get install -y trivy
echo "✅ Trivy installed."

echo "🎉 All dependencies installed successfully!"

