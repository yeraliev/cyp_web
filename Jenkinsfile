pipeline {
    agent any

    triggers {
        // Jenkins runs on a local machine and cannot receive GitHub webhooks,
        // so it checks the repository for new commits every 2 minutes
        pollSCM('H/2 * * * *')
    }

    options {
        // The Checkout stage below does it explicitly
        skipDefaultCheckout()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        IMAGE = 'cyp-web'
        TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build test image') {
            steps {
                sh 'docker build --target test -t $IMAGE-test:$TAG .'
            }
        }

        stage('Lint') {
            steps {
                sh 'docker run --rm $IMAGE-test:$TAG flake8 . --select=E9,F63,F7,F82 --show-source --statistics'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'docker create --name $IMAGE-test-$TAG $IMAGE-test:$TAG'
                sh 'docker start -a $IMAGE-test-$TAG'
            }
            post {
                always {
                    sh 'docker cp $IMAGE-test-$TAG:/app/test-results.xml . || true'
                    sh 'docker rm -f $IMAGE-test-$TAG || true'
                    junit allowEmptyResults: true, testResults: 'test-results.xml'
                }
            }
        }

        stage('Build Docker image') {
            steps {
                sh 'docker build --target app -t $IMAGE:$TAG -t $IMAGE:latest .'
            }
        }

        stage('Smoke test image') {
            steps {
                // The container must rebuild the yearly dataset without errors
                sh 'docker run --rm $IMAGE:$TAG'
            }
        }
    }

    post {
        always {
            sh 'docker rmi $IMAGE-test:$TAG || true'
        }
        success {
            echo "Image ${IMAGE}:${TAG} is ready"
        }
    }
}
