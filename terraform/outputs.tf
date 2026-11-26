output "ec2_public_ip" {
  description = "Địa chỉ Public IP của máy chủ EC2"
  value       = aws_instance.k3s_server.public_ip
}

output "ssh_command" {
  description = "Lệnh SSH trực tiếp vào máy chủ EC2"
  value       = var.existing_key_name == "" ? "ssh -i ai-diagnosis-key.pem ubuntu@${aws_instance.k3s_server.public_ip}" : "ssh -i <YOUR_KEY>.pem ubuntu@${aws_instance.k3s_server.public_ip}"
}

output "argocd_web_url" {
  description = "Đường dẫn truy cập giao diện trực quan ArgoCD Web Dashboard"
  value       = "http://${aws_instance.k3s_server.public_ip}:30088"
}

output "argocd_admin_password_command" {
  description = "Lệnh lấy mật khẩu ban đầu của tài khoản admin ArgoCD"
  value       = "ssh ${var.existing_key_name == "" ? "-i ai-diagnosis-key.pem" : ""} ubuntu@${aws_instance.k3s_server.public_ip} 'cat ~/argocd-admin-password.txt || kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d'"
}

output "voting_app_url" {
  description = "Địa chỉ truy cập Voting App (thêm header Host: voting.local hoặc cấu hình /etc/hosts)"
  value       = "http://${aws_instance.k3s_server.public_ip}:30080"
}
