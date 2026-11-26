# Tìm kiếm Ubuntu 24.04 LTS AMI chính thức mới nhất tại us-east-1 (nếu không truyền custom_ami_id)
data "aws_ami" "ubuntu" {
  count       = var.custom_ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["099720109477"] # Canonical ID chính chủ

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  ami_id = var.custom_ami_id != "" ? var.custom_ami_id : data.aws_ami.ubuntu[0].id
}

# Khởi tạo EC2 Instance đóng vai trò K8s Node & ArgoCD Server
resource "aws_instance" "k3s_server" {
  ami                         = local.ami_id
  instance_type               = var.instance_type
  key_name                    = local.selected_key_name
  vpc_security_group_ids      = [aws_security_group.k3s_node_sg.id]
  subnet_id                   = tolist(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = true

  # Cấu hình ổ cứng lưu trữ hệ điều hành và dữ liệu
  root_block_device {
    volume_size           = var.volume_size
    volume_type           = "gp3"
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-root-volume"
    }
  }

  # Nạp script tự động cài đặt k3s, Helm, NGINX Ingress, ArgoCD
  user_data = file("${path.module}/user_data.sh.tpl")

  tags = {
    Name = "${var.project_name}-server"
    Role = "Kubernetes-ControlPlane-and-Worker"
  }
}
