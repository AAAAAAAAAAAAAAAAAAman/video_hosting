# videos_host/models.py
from django.db import models
from django.utils import timezone


class Video(models.Model):
    title = models.CharField(max_length=255, verbose_name="视频标题")
    upload_time = models.DateTimeField(default=timezone.now, verbose_name="上传时间")
    # video_url 字段保持唯一性
    video_url = models.URLField(max_length=216, verbose_name="视频URL")
    thumbnail_url = models.URLField(max_length=2000, verbose_name="封面图片URL", blank=True, null=True)
    views = models.IntegerField(default=0, verbose_name="访问量")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "视频"
        verbose_name_plural = "视频"
        ordering = ['-upload_time']