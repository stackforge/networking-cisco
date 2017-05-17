#!groovy
pipeline {
  agent { label 'ci-runner' }
  options {
    timeout(time: 20, unit: 'MINUTES')
  }
  stages {
    stage('Clean workspace') {
      steps {
        sh '''
          git clean -f -d
          make clean
        '''
      }
    }
    stage('Python package: pep8  (premerge)') {
      steps {
        sh '''
          make clean pep8
        '''
      }
    }
    stage('Python package: build package (premerge)') {
      steps {
        sh '''
          make build
        '''
      }
    }
    stage('Python package: upload to devpi (premerge)') {
      steps {
        withCredentials([[$class: "UsernamePasswordMultiBinding",
                          credentialsId: "harmony-networking-cisco-devpi-premerge",
                          usernameVariable: "USERNAME",
                          passwordVariable: "PASSWORD"]]) {
          sh '''
              devpi use https://pypi.ci.dfj.io/harmony_networking-cisco_premerge/premerge
              devpi login "$USERNAME" --password="$PASSWORD"
              devpi upload dist/*
          '''
        }
      }
    }
    stage('Docker image: kolla-build (premerge)') {
      steps {
        sh '''
          export DOCKER_CONFIG=$WORKSPACE
          make kolla-build-premerge
        '''
      }
    }
  }
}
