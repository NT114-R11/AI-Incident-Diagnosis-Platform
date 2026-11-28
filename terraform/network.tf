# Sử dụng Default VPC của AWS (tương thích 100% với AWS Academy, không cần tạo VPC thủ công)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group mở các cổng dịch vụ cần thiết cho Đồ án
resource "aws_security_group" "k3s_node_sg" {
  name_prefix = "${var.project_name}-sg-"
  description = "Security group for AI Incident Diagnosis Platform on k3s"
  vpc_id      = data.aws_vpc.default.id

  lifecycle {
    create_before_destroy = true
  }

  # SSH
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidr
  }

  # HTTP / HTTPS
  ingress {
    description = "HTTP access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS access"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # NGINX Ingress NodePort cho Voting App
  ingress {
    description = "Voting App Ingress HTTP NodePort"
    from_port   = 30080
    to_port     = 30080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Voting App Ingress HTTPS NodePort"
    from_port   = 30443
    to_port     = 30443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # ArgoCD Web UI NodePort (truy cập trực tiếp dashboard)
  ingress {
    description = "ArgoCD Web UI NodePort"
    from_port   = 30088
    to_port     = 30088
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Cổng 8080 phòng hờ
  ingress {
    description = "Alternate HTTP / Port forward"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana Dashboard NodePort (nếu expose trực tiếp)
  ingress {
    description = "Grafana Dashboard"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress mở toàn bộ để kéo Docker image, Helm charts, Google AI Studio API, Telegram API
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}
