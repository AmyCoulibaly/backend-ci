pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        IMAGE_NAME            = "${DOCKERHUB_CREDENTIALS_USR}/esante-senegal-backend"
        IMAGE_TAG             = "${env.BUILD_NUMBER}"
        PYTHONUNBUFFERED      = "1"
        FLASK_ENV             = "testing"
    }

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Pytest') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/ -v
                '''
            }
        }

        stage('Bandit (SAST)') {
            steps {
                sh '''
                    . .venv/bin/activate
                    bandit -r app/ -ll -ii
                '''
            }
        }

        stage('pip-audit') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pip-audit -r requirements.txt --desc || true
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t $IMAGE_NAME:$IMAGE_TAG -t $IMAGE_NAME:latest .'
            }
        }

        stage('Trivy Scan') {
            steps {
                sh '''
                    trivy image --exit-code 0 --severity MEDIUM,HIGH $IMAGE_NAME:$IMAGE_TAG || true
                    trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed $IMAGE_NAME:$IMAGE_TAG
                '''
            }
        }

        stage('Docker Push') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                sh '''
                    echo "$DOCKERHUB_CREDENTIALS_PSW" | docker login -u "$DOCKERHUB_CREDENTIALS_USR" --password-stdin
                    docker push $IMAGE_NAME:$IMAGE_TAG
                    docker push $IMAGE_NAME:latest
                    docker logout
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f || true'
        }
        success {
            echo 'Pipeline CI backend terminé avec succès.'
        }
        failure {
            echo 'Pipeline CI backend en échec.'
        }
    }
}
