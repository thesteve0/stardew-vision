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

# The common-utils feature will now be able to create the user with the specified UID