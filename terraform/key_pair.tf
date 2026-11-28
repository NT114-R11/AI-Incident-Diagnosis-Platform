# Tự động tạo SSH Key Pair nếu người dùng không chỉ định key_name có sẵn
resource "tls_private_key" "ec2_key" {
  count     = var.existing_key_name == "" ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  count           = var.existing_key_name == "" ? 1 : 0
  key_name_prefix = "${var.project_name}-key-"
  public_key      = tls_private_key.ec2_key[0].public_key_openssh

  lifecycle {
    create_before_destroy = true
  }
}

# Lưu private key về thư mục terraform để người dùng SSH trực tiếp
resource "local_file" "private_key_pem" {
  count           = var.existing_key_name == "" ? 1 : 0
  content         = tls_private_key.ec2_key[0].private_key_pem
  filename        = "${path.module}/ai-diagnosis-key.pem"
  file_permission = "0400"
}

locals {
  selected_key_name = var.existing_key_name != "" ? var.existing_key_name : aws_key_pair.generated_key[0].key_name
}

