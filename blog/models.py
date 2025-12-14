from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

User = get_user_model()


class Post(models.Model):
    """Main Blog Post Model"""

    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name='عنوان',
        help_text='عنوان پست بلاگ (حداکثر 255 کاراکتر)'
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name='اسلاگ',
        help_text='URL خودکار از عنوان ساخته می‌شود',
        db_index=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='نویسنده',
        help_text='ادمینی که این پست را نوشته است'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='وضعیت',
        help_text='وضعیت انتشار پست',
        db_index=True
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ انتشار',
        help_text='زمان انتشار پست (اگر منتشر شده باشد)',
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد',
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )
    meta_description = models.TextField(
        max_length=160,
        blank=True,
        verbose_name='توضیحات متا',
        help_text='توضیحات برای SEO (حداکثر 160 کاراکتر)'
    )
    featured_image = models.ImageField(
        upload_to='posts/featured/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='تصویر شاخص',
        help_text='تصویر اصلی پست که در لیست و صفحه پست نمایش داده می‌شود'
    )

    class Meta:
        verbose_name = 'پست'
        verbose_name_plural = 'پست‌ها'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at'], name='post_status_pub_idx'),
            models.Index(fields=['author', '-created_at'], name='post_author_date_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    def is_published(self):
        """Checking if the post has been published or not"""
        return self.status == 'published' and self.published_at is not None

    def get_sections_count(self):
        """Number of post sections"""
        return self.sections.count()

    def get_text_sections(self):
        """Get text segments"""
        return self.sections.filter(section_type='text')

    def get_media_sections(self):
        """Get image segments"""
        return self.sections.filter(section_type__in=['image', 'gallery', 'video'])


class PostSection(models.Model):
    """Different sections within each post"""

    SECTION_TYPE_CHOICES = [
        ('text', 'متن'),
        ('image', 'تصویر'),
        ('gallery', 'گالری تصاویر'),
        ('quote', 'نقل قول'),
        ('code', 'کد'),
        ('video', 'ویدیو'),
    ]

    POSITION_CHOICES = [
        ('top-left', 'بالا - چپ'),
        ('top-center', 'بالا - وسط'),
        ('top-right', 'بالا - راست'),
        ('middle-left', 'وسط - چپ'),
        ('middle-center', 'وسط - وسط'),
        ('middle-right', 'وسط - راست'),
        ('bottom-left', 'پایین - چپ'),
        ('bottom-center', 'پایین - وسط'),
        ('bottom-right', 'پایین - راست'),
        ('custom', 'سفارشی'),
    ]

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name='پست',
        help_text='پستی که این بخش به آن تعلق دارد'
    )
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_TYPE_CHOICES,
        verbose_name='نوع بخش',
        help_text='نوع محتوای این بخش',
        db_index=True
    )
    content = models.TextField(
        verbose_name='محتوا',
        help_text='محتوای متنی'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='ترتیب',
        help_text='ترتیب نمایش این بخش (عدد کوچکتر = بالاتر)',
        db_index=True
    )
    position_choice = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default='top-center',
        verbose_name='موقعیت',
        help_text='موقعیت از پیش تعریف شده - اگر "سفارشی" انتخاب شود، position_x و position_y استفاده می‌شود'
    )
    position_x = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='موقعیت افقی',
        help_text='موقعیت X سفارشی (مثلا: 10%, 50px, 2rem) - فقط برای موقعیت سفارشی'
    )
    position_y = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='موقعیت عمودی',
        help_text='موقعیت Y سفارشی (مثلا: 20%, 100px, 5rem) - فقط برای موقعیت سفارشی'
    )
    width = models.CharField(
        max_length=20,
        default='100%',
        verbose_name='عرض',
        help_text='عرض بخش (مثلا: 100%, 500px, auto)'
    )
    height = models.CharField(
        max_length=20,
        default='auto',
        verbose_name='ارتفاع',
        help_text='ارتفاع بخش (مثلا: auto, 300px, 50vh)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        verbose_name = 'بخش پست'
        verbose_name_plural = 'بخش‌های پست'
        ordering = ['post', 'order']
        indexes = [
            models.Index(fields=['post', 'order'], name='section_post_order_idx'),
            models.Index(fields=['post', 'section_type'], name='section_post_type_idx'),
        ]

    def __str__(self):
        return f"{self.post.title} - {self.get_section_type_display()} ({self.order})"

    def get_position_style(self):
        """CSS Style"""
        if self.position_choice == 'custom' and self.position_x and self.position_y:
            return {
                'position': 'absolute',
                'left': self.position_x,
                'top': self.position_y,
                'width': self.width,
                'height': self.height,
            }

        # موقعیت‌های از پیش تعریف شده
        position_map = {
            'top-left': {'top': '0', 'left': '0'},
            'top-center': {'top': '0', 'left': '50%', 'transform': 'translateX(-50%)'},
            'top-right': {'top': '0', 'right': '0'},
            'middle-left': {'top': '50%', 'left': '0', 'transform': 'translateY(-50%)'},
            'middle-center': {'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)'},
            'middle-right': {'top': '50%', 'right': '0', 'transform': 'translateY(-50%)'},
            'bottom-left': {'bottom': '0', 'left': '0'},
            'bottom-center': {'bottom': '0', 'left': '50%', 'transform': 'translateX(-50%)'},
            'bottom-right': {'bottom': '0', 'right': '0'},
        }

        style = position_map.get(self.position_choice, {})
        style.update({'width': self.width, 'height': self.height})
        return style

    def is_media_section(self):
        """Checking if a section contains media"""
        return self.section_type in ['image', 'gallery', 'video']


class Media(models.Model):
    """Media files (photos, videos, audio)"""

    FILE_TYPE_CHOICES = [
        ('image', 'تصویر'),
        ('video', 'ویدیو'),
        ('audio', 'صوت'),
    ]

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='media',
        verbose_name='پست',
        help_text='پستی که این فایل به آن تعلق دارد'
    )
    section = models.ForeignKey(
        PostSection,
        on_delete=models.CASCADE,
        related_name='media',
        null=True,
        blank=True,
        verbose_name='بخش',
        help_text='بخش خاصی که این فایل در آن استفاده شده (اختیاری)'
    )
    file = models.FileField(
        upload_to='posts/media/%Y/%m/%d/',
        verbose_name='فایل',
        help_text='فایل رسانه‌ای (عکس، ویدیو، صوت)',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mp3', 'wav']
            )
        ]
    )
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        verbose_name='نوع فایل',
        help_text='نوع فایل برای نمایش صحیح',
        db_index=True
    )
    file_size = models.PositiveIntegerField(
        verbose_name='حجم فایل',
        help_text='حجم فایل به بایت - برای مدیریت فضای ذخیره‌سازی',
        null=True,
        blank=True
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='متن جایگزین',
        help_text='توضیح تصویر برای SEO و دسترسی‌پذیری'
    )
    caption = models.TextField(
        blank=True,
        verbose_name='کپشن',
        help_text='کپشن برای نمایش زیر تصویر'
    )
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='عرض',
        help_text='عرض تصویر/ویدیو به پیکسل'
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ارتفاع',
        help_text='ارتفاع تصویر/ویدیو به پیکسل'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ آپلود',
        db_index=True
    )

    class Meta:
        verbose_name = 'فایل رسانه‌ای'
        verbose_name_plural = 'فایل‌های رسانه‌ای'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'file_type'], name='media_post_type_idx'),
            models.Index(fields=['post', '-created_at'], name='media_post_date_idx'),
        ]

    def __str__(self):
        return f"{self.get_file_type_display()} - {self.post.title}"

    def save(self, *args, **kwargs):
        """Automatic file size calculation"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        if not self.file_size:
            return "نامشخص"

        size = self.file_size
        for unit in ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ترابایت"

    def is_image(self):
        return self.file_type == 'image'

    def is_video(self):
        return self.file_type == 'video'

    def get_thumbnail_tag(self):
        """HTML tag to display thumbnail in admin"""
        if self.is_image():
            return f'<img src="{self.file.url}" width="100" height="100" style="object-fit: cover;" />'
        return '—'


class Layout(models.Model):
    """Pre-built templates for quick layout"""

    name = models.CharField(
        max_length=100,
        verbose_name='نام قالب',
        help_text='نام توصیفی برای این قالب'
    )
    description = models.TextField(
        blank=True,
        verbose_name='توضیحات',
        help_text='توضیح کامل درباره این قالب و کاربردش'
    )
    template_json = models.JSONField(
        verbose_name='تنظیمات قالب',
        help_text='ساختار JSON شامل موقعیت‌ها و تنظیمات بخش‌ها',
        default=dict
    )
    thumbnail = models.ImageField(
        upload_to='layouts/thumbnails/',
        blank=True,
        null=True,
        verbose_name='تصویر نمونه',
        help_text='تصویر پیش‌نمایش قالب'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال',
        help_text='قالب‌های غیرفعال در لیست نمایش داده نمی‌شوند',
        db_index=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        verbose_name = 'قالب'
        verbose_name_plural = 'قالب‌ها'
        ordering = ['-is_active', 'name']

    def __str__(self):
        return self.name

    def get_sections_count(self):
        """Number of sections defined in the template"""
        if isinstance(self.template_json, dict) and 'sections' in self.template_json:
            return len(self.template_json['sections'])
        return 0
