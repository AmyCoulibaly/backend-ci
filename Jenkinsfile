pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        IMAGE_NAME            = "${DOCKERHUB_CREDENTIALS_USR}/esante-senegal-backend"
        GIT_SHORT_SHA         = "${env.GIT_COMMIT?.take(7) ?: 'unknown'}"
        IMAGE_TAG             = "${GIT_SHORT_SHA}-${env.BUILD_NUMBER}"
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
                    pip install -r requirements-dev.txt
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
                    bandit -r app/ -ll -ii -f json -o bandit-report.json --exit-zero
                    bandit -r app/ -ll -ii -f txt -o bandit-report.txt --exit-zero
                    bandit -r app/ -ll -ii
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'bandit-report.*', allowEmptyArchive: true
                }
            }
        }

        stage('Vérification des dépendances (pip-audit)') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pip-audit -r requirements.txt --desc -f json -o pip-audit-report.json || true
                    pip-audit -r requirements.txt --desc
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'pip-audit-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh """
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                """
            }
        }

        stage('Scan de vulnérabilités (Trivy)') {
            steps {
                sh """
                    trivy image --exit-code 0 --severity MEDIUM,HIGH ${IMAGE_NAME}:${IMAGE_TAG} | tee trivy-report.txt
                    trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed ${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.txt', allowEmptyArchive: true
                }
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
            echo "Pipeline CI backend-ci : ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo "Échec du pipeline CI backend-ci. Consultez les journaux d'étape."
        }
    }
}
