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
        timestamps()
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
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Pytest') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest tests/ -v --junitxml=pytest-report.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'pytest-report.xml'
                }
            }
        }

        stage('Scan de sécurité du code (Bandit)') {
            steps {
                sh '''
                    . .venv/bin/activate
                    bandit -r app/ -ll -ii -f json -o bandit-report.json || true
                    bandit -r app/ -ll -ii
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                '''
            }
        }

        stage('Scan de vulnérabilités (Trivy)') {
            steps {
                sh '''
                    trivy image --exit-code 0 --severity MEDIUM,HIGH ${IMAGE_NAME}:${IMAGE_TAG}
                    trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Docker Push vers Docker Hub') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                sh '''
                    echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin
                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                    docker push ${IMAGE_NAME}:latest
                    docker logout
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f || true'
            cleanWs()
        }
        success {
            echo "Pipeline CI backend-ci exécuté avec succès : ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "Échec du pipeline CI backend-ci. Consultez les journaux d'étape."
        }
    }
}
