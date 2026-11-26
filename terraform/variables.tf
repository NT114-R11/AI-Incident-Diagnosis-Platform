variable "aws_region" {
  description = "AWS region to deploy infrastructure (AWS Academy Learner Lab BẮT BUỘC dùng us-east-1)"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name tag and prefix"
  type        = string
  default     = "ai-incident-diagnosis-platform"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 Instance type (t3.large: 2 vCPU, 8GB RAM - đủ chạy k3s, apps, monitoring, ArgoCD)"
  type        = string
  default     = "t3.large"
}

variable "volume_size" {
  description = "Root EBS volume size in GB (Lưu trữ Docker images, Prometheus TSDB, Loki logs)"
  type        = number
  default     = 40
}

variable "allowed_ssh_cidr" {
  description = "CIDR block permitted for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "existing_key_name" {
  description = "Tên Key Pair có sẵn trên AWS (nếu để trống, Terraform sẽ tự động tạo SSH key mới và lưu file .pem về máy)"
  type        = string
  default     = ""
}

variable "custom_ami_id" {
  description = "Chỉ định trực tiếp AMI ID nếu không muốn query AMI (để trống để tự động tìm Ubuntu 24.04)"
  type        = string
  default     = ""
}
