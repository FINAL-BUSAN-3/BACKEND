pipeline {
	agent any
	stages {
		stage('[BACKEND] Start') {
			steps {
				sh 'echo "[BACKEND] Start"'
				slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[Schedule Sync] Start : Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
			}
		}
		stage('[BACKEND] Git clone') {
                        steps {
                            script{
                                def localUser = 'ubuntu'
                                def localHost = 'ec2-18-215-52-54.compute-1.amazonaws.com'
                                def pemPath = '/var/jenkins_home/busan.pem'

                                sh 'echo "[Schedule Sync] Git clone"'
                                sh """
                                ssh -i ${pemPath} ${localUser}@${localHost} "cd /home/ubuntu/BACKEND && git pull"
                                """

                                slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[WEB] GIT PULL : Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
                            }
                        }
                }
		stage('[BACKEND] SERVER DOWN') {
			steps{
				script{
					def localUser = 'ubuntu'
                    def localHost = 'ec2-18-215-52-54.compute-1.amazonaws.com'
                    def pemPath = '/var/jenkins_home/busan.pem'


					sh """
                    ssh -i ${pemPath} ${localUser}@${localHost} "pm2 delete backend || echo '0'"
                    """
                    sh 'echo "[BACKEND] SERVER DOWN"'

					slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[WEB] SERVER DOWN : Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
				}
			}

		}
		stage('[WEB] WEB SERVER UP') {
			steps{
				script{
					def localUser = 'ubuntu'
                    def localHost = 'ec2-18-215-52-54.compute-1.amazonaws.com'
                    def pemPath = '/var/jenkins_home/busan.pem'

					sh """
                    ssh -i ${pemPath} ${localUser}@${localHost} "cd /home/ubuntu/BACKEND/fastapi && pm2 start \"uvicorn main:app --host 0.0.0.0 --port 8000\" --name backend "
                    """
                    sh 'echo "[BACKEND] SERVER ON"'
					slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[WEB] SERVER ON : Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
				}
			}
		}
		stage('[WEB] Done') {
                        steps {
				sh 'echo "[WEB] Done"'
                                slackSend(channel: '#deployment-alert', color: '#00FF7F' , message: "[WEB] Done : Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' (${env.BUILD_URL})")
			}
                }
		
	}
}
