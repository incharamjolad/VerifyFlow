pipeline {
  // Windows Jenkins agent (Jenkins installed on the same PC as Docker Desktop + Minikube)
  agent any
  environment { TAG = "${env.BUILD_NUMBER}" }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Backend tests') {
      steps { dir('backend') { bat 'python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt && .venv\\Scripts\\python -m pytest -q' } }
    }
    stage('Frontend build') {
      steps { dir('frontend') { bat 'npm install && npm run build' } }
    }
    stage('Build images') {
      steps {
        bat 'docker build -t verifyflow-backend:%TAG% backend'
        bat 'docker build -t verifyflow-frontend:%TAG% frontend'
      }
    }
    stage('Deploy to Minikube') {
      steps {
        bat 'minikube image load verifyflow-backend:%TAG%'
        bat 'minikube image load verifyflow-frontend:%TAG%'
        bat 'kubectl apply -f k8s/configmap.yaml -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml'
        bat 'kubectl set image deployment/backend backend=verifyflow-backend:%TAG%'
        bat 'kubectl set image deployment/frontend frontend=verifyflow-frontend:%TAG%'
        bat 'kubectl rollout status deployment/backend --timeout=180s'
        bat 'kubectl rollout status deployment/frontend --timeout=180s'
      }
    }
  }
  post {
    success { echo 'Build, tests and deployment succeeded.' }
    failure { echo 'Pipeline failed - later stages (including deploy) did not run.' }
  }
}
