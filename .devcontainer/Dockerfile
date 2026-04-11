# ROCm PyTorch ML Development Container
# Base: Official AMD ROCm PyTorch image (Ubuntu 24.04)
FROM rocm/pytorch:rocm7.2_ubuntu24.04_py3.12_pytorch_release_2.9.1

# Workaround for Ubuntu 24.04 having pre-existing ubuntu user at UID 1000
# This prevents common-utils from creating users at UID 1001
# See: https://github.com/devcontainers/images/issues/1056
RUN touch /var/mail/ubuntu && chown ubuntu /var/mail/ubuntu && userdel -r ubuntu


# Install uv package manager into /opt/venv (not bundled in ROCm 7.2 unlike 7.1)
# Symlink to /usr/local/bin so it's in PATH for all users
RUN /opt/venv/bin/pip install uv && \
    ln -s /opt/venv/bin/uv /usr/local/bin/uv

# Install Kubernetes, OpenShift, and Cloud CLI tools
# Installing as binaries to /usr/local/bin for better control and consistency
RUN set -e && \
    # Detect architecture
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then ARCH="amd64"; elif [ "$ARCH" = "aarch64" ]; then ARCH="arm64"; fi && \
    \
    # Install kubectl (Kubernetes CLI)
    KUBECTL_VERSION=$(curl -sL https://dl.k8s.io/release/stable.txt) && \
    curl -sL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" -o /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl && \
    \
    # Install oc (OpenShift CLI)
    OC_VERSION="latest" && \
    curl -sL "https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/${OC_VERSION}/openshift-client-linux.tar.gz" | \
    tar xzf - -C /usr/local/bin oc kubectl && \
    chmod +x /usr/local/bin/oc && \
    \
    # Install k9s (Kubernetes dashboard)
    K9S_VERSION=$(curl -s https://api.github.com/repos/derailed/k9s/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/') && \
    curl -sL "https://github.com/derailed/k9s/releases/download/v${K9S_VERSION}/k9s_Linux_${ARCH}.tar.gz" | \
    tar xzf - -C /usr/local/bin k9s && \
    chmod +x /usr/local/bin/k9s && \
    \
    # Install krew (kubectl plugin manager)
    cd /tmp && \
    KREW_VERSION=$(curl -s https://api.github.com/repos/kubernetes-sigs/krew/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/') && \
    curl -sL "https://github.com/kubernetes-sigs/krew/releases/download/v${KREW_VERSION}/krew-linux_${ARCH}.tar.gz" | \
    tar xzf - && \
    ./krew-linux_${ARCH} install krew && \
    mv /root/.krew/bin/kubectl-krew /usr/local/bin/ && \
    rm -rf /tmp/krew-linux_${ARCH} && \
    \
    # Install GitHub CLI
    GH_VERSION=$(curl -s https://api.github.com/repos/cli/cli/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/') && \
    curl -sL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${ARCH}.tar.gz" | \
    tar xzf - --strip-components=2 -C /usr/local/bin "gh_${GH_VERSION}_linux_${ARCH}/bin/gh" && \
    chmod +x /usr/local/bin/gh && \
    \
    # Install AWS CLI v2
    cd /tmp && \
    curl -sL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip && \
    unzip -q awscliv2.zip && \
    ./aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli && \
    rm -rf /tmp/awscliv2.zip /tmp/aws && \
    \
    # Verify installations
    echo "Installed CLI tools:" && \
    kubectl version --client --short 2>/dev/null || kubectl version --client && \
    oc version --client && \
    k9s version --short && \
    kubectl-krew version && \
    gh --version && \
    aws --version

# The common-utils feature will now be able to create the user with the specified UID

# Note: Claude CLI is installed via postCreateCommand in setup-environment.sh
# (runs as the devcontainer user, not root, for proper permissions)