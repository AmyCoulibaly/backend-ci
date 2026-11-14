pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        IMAGE_NAME            = "${DOCKERHUB_CREDENTIALS_USR}/esante-senegal-backend"
        IMAGE_TAG             = "${env.BUILD_NUMBER}"
        TEST_IMAGE            = 'esante-backend-test'
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

        stage('Tests et Analyse de sécurité') {
            steps {
                sh 'docker build --target test -t $TEST_IMAGE .'
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
