pipeline {

	agent any
	stages {
		stage('test-stage') {
			steps {
				slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[TEST]STARTED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
			}
		}
		stage('test-stage-2') {
                        steps {
                                slackSend(channel: '#deployment-alert', color: '#FF0000' , message: "[TEST]ERROR: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
                        }
                }
		stage('test-stage-3') {
                        steps {
                                slackSend(channel: '#deployment-alert', color: '#FFFFE0' , message: "[TEST]WARNING: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
                        }
                }
		
	}
}
