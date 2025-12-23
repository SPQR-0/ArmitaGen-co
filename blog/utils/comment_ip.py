from blog.models import CommenterIP


def get_or_create_commenter_ip(ip: str) -> CommenterIP:
    obj, _ = CommenterIP.objects.get_or_create(ip_address=ip)
    return obj
