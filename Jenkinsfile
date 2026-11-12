pipeline {
  agent any
  environment { TAG = "${env.BUILD_NUMBER}" }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Backend tests') {
      steps { dir('backend') { sh 'pip install -r requirements.txt && pytest -q' } }
    }
    stage('Frontend build') {
      steps { dir('frontend') { sh 'npm install && npm run build' } }
    }
    stage('Build images') {
      steps {
        sh 'docker build -t verifyflow-backend:${TAG} backend'
        sh 'docker build -t verifyflow-frontend:${TAG} frontend'
      }
    }
    stage('Deploy to Minikube') {
      steps {
        sh 'minikube image load verifyflow-backend:${TAG} && minikube image load verifyflow-frontend:${TAG}'
        sh 'kubectl apply -f k8s/configmap.yaml -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml'
        sh 'kubectl set image deployment/backend backend=verifyflow-backend:${TAG} && kubectl set image deployment/frontend frontend=verifyflow-frontend:${TAG}'
        sh 'kubectl rollout status deployment/backend && kubectl rollout status deployment/frontend'
      }
    }
  }
  post { failure { echo 'Pipeline failed - nothing was deployed from this build.' } }
}
