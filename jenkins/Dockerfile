# Jenkins server with Docker CLI, the needed plugins and a ready pipeline job
FROM jenkins/jenkins:lts-jdk21

USER root
# Docker CLI and buildx; the builds run on the host Docker through the mounted socket
COPY --from=docker:28-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:28-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY casc.yaml /usr/share/jenkins/ref/casc.yaml

# Skip the setup wizard; users and the job come from casc.yaml
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false" \
    CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc.yaml
