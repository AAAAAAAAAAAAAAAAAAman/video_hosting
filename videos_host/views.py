# videos_host/views.py
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Video
from django.http import HttpResponse, JsonResponse
import os  # 用于生成唯一的视频URL
from datetime import datetime
from django.conf import settings # 导入 settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
# 获取一个 logger（推荐使用模块名）
logger = logging.getLogger(__name__)


@csrf_exempt
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 记录登录尝试
        logger.info(f"管理员登录尝试: 用户名='{username}', IP={get_client_ip(request)}")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            logger.info(f"管理员登录成功: 用户名='{username}', IP={get_client_ip(request)}")
            return redirect('admin_dashboard')
        else:
            logger.warning(f"管理员登录失败: 用户名='{username}', IP={get_client_ip(request)}")
            return render(request, 'videos/admin_login.html', {'error': '用户名或密码错误'})

    return render(request, 'videos/admin_login.html')


def admin_logout(request):
    username = request.user.username if request.user.is_authenticated else "Unknown"
    ip = get_client_ip(request)
    logout(request)
    logger.info(f"管理员登出: 用户名='{username}', IP={ip}")
    return redirect('admin_login')


@login_required(login_url='admin_login')
def admin_dashboard(request):
    search_query = request.GET.get('q', '')
    if search_query:
        videos = Video.objects.filter(title__icontains=search_query)
    else:
        videos = Video.objects.all()

    # 记录访问仪表盘
    logger.info(
        f"管理员访问仪表盘: 用户名='{request.user.username}', "
        f"搜索词='{search_query}', 视频数量={videos.count()}, IP={get_client_ip(request)}"
    )

    # 计算 media/videos/ 目录下所有视频文件的总大小
    videos_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
    total_size = 0

    if os.path.exists(videos_dir):
        for filename in os.listdir(videos_dir):
            file_path = os.path.join(videos_dir, filename)
            if os.path.isfile(file_path):
                try:
                    total_size += os.path.getsize(file_path)
                except OSError as e:
                    logger.error(f"无法读取视频文件大小: {file_path}, 错误={e}")
                    pass

    readable_size = bytes_to_readable(total_size)

    context = {
        'videos': videos,
        'search_query': search_query,
        'total_video_count': videos.count(),
        'total_storage_used': readable_size,
    }
    return render(request, 'videos/admin_dashboard.html', context)


# 工具函数：获取客户端真实 IP（考虑反向代理）
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# 工具函数：将字节转换为可读格式
def bytes_to_readable(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"


@login_required(login_url='admin_login')
def admin_delete_video(request, video_id):
    ip = get_client_ip(request)
    username = request.user.username

    if request.method != 'POST':
        logger.warning(f"非法删除请求方法: video_id={video_id}, 用户='{username}', IP={ip}, 方法={request.method}")
        return JsonResponse({'status': 'error'}, status=405)

    video = get_object_or_404(Video, pk=video_id)
    video_title = video.title
    video_url = video.video_url
    thumbnail_url = video.thumbnail_url

    # 构建文件路径
    video_path = None
    if video.video_url:
        relative_path = video.video_url.replace('/media/', '', 1)
        video_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    thumbnail_path = None
    if video.thumbnail_url:
        relative_path = video.thumbnail_url.replace('/media/', '', 1)
        thumbnail_path = os.path.join(settings.MEDIA_ROOT, relative_path)

    # 记录删除操作开始
    logger.info(
        f"管理员开始删除视频: 视频ID={video_id}, 标题='{video_title}', "
        f"视频文件='{video_path}', 封面='{thumbnail_path}', 用户='{username}', IP={ip}"
    )

    # 先从数据库删除
    video.delete()
    logger.info(f"数据库记录已删除: 视频ID={video_id}, 标题='{video_title}'")

    # 删除物理文件
    deleted_files = []
    for file_path in [video_path, thumbnail_path]:
        if file_path and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
                logger.info(f"物理文件已删除: 文件='{file_path}', 操作者='{username}', IP={ip}")
            except Exception as e:
                logger.error(f"删除文件失败: 文件='{file_path}', 错误={str(e)}, 用户='{username}', IP={ip}")

    # 返回响应
    response_data = {
        'status': 'success',
        'deleted_files': len(deleted_files),
        'video_id': video_id,
        'title': video_title
    }

    logger.info(
        f"视频删除成功: 视频ID={video_id}, 标题='{video_title}', "
        f"共删除 {len(deleted_files)} 个文件, 用户='{username}', IP={ip}"
    )
    return JsonResponse(response_data)


# 用户观看视频页面
def watch_video(request, video_filename):
    ip = get_client_ip(request)
    logger.info(f"用户请求观看视频: 文件名='{video_filename}', IP={ip}")

    try:
        video = Video.objects.get(video_url__endswith=f"/{video_filename}")
        old_views = video.views
        video.views += 1
        video.save()

        logger.info(
            f"视频观看记录更新: 视频ID={video.id}, 标题='{video.title}', "
            f"播放量 {old_views} → {video.views}, IP={ip}"
        )

        return render(request, 'videos/watch_video.html', {'video': video})
    except Video.DoesNotExist:
        logger.warning(f"用户请求的视频不存在: 文件名='{video_filename}', IP={ip}")
        return HttpResponse("视频不存在或链接有误！", status=404)

@login_required(login_url='admin_login')
def admin_video_edit(request, video_id=None):
    video = get_object_or_404(Video, pk=video_id) if video_id else None
    ip = get_client_ip(request)
    username = request.user.username

    # 记录访问编辑页面
    if video:
        logger.info(f"管理员访问视频编辑页面: 视频ID={video.id}, 标题='{video.title}', 用户='{username}', IP={ip}")
    else:
        logger.info(f"管理员访问新增视频页面: 用户='{username}', IP={ip}")

    if request.method == 'POST':
        title = request.POST.get('title')
        thumbnail_file = request.FILES.get('thumbnail_file')
        video_file = request.FILES.get('video_file')

        if video:
            # ========== 修改现有视频 ==========
            old_title = video.title
            old_video_url = video.video_url
            old_thumbnail_url = video.thumbnail_url

            logger.info(f"管理员开始修改视频: 视频ID={video.id}, 原标题='{old_title}', 新标题='{title}', 用户='{username}', IP={ip}")

            video.title = title

            # 处理新视频文件上传
            if video_file:
                current_time = datetime.now().strftime('%Y%m%d%H%M%S')
                clean_title = slugify(title)
                filename = f"{current_time}-{clean_title}.mp4"
                save_path = os.path.join(settings.MEDIA_ROOT, 'videos', filename)

                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                try:
                    with open(save_path, 'wb+') as destination:
                        for chunk in video_file.chunks():
                            destination.write(chunk)
                    # 删除旧视频文件（可选）
                    if old_video_url and os.path.isfile(save_path.replace(filename, old_video_url.split('/')[-1])):
                        try:
                            os.remove(save_path.replace(filename, old_video_url.split('/')[-1]))
                            logger.info(f"旧视频文件已删除: {old_video_url}, 用户='{username}', IP={ip}")
                        except Exception as e:
                            logger.warning(f"删除旧视频文件失败: {old_video_url}, 错误={e}")

                    video.video_url = f"{settings.MEDIA_URL}videos/{filename}"
                    logger.info(f"视频文件已更新: 新文件='{filename}', 用户='{username}', IP={ip}")
                except Exception as e:
                    logger.error(f"上传视频文件失败: 标题='{title}', 错误={str(e)}, 用户='{username}', IP={ip}")
                    return render(request, 'videos/admin_video_edit.html', {
                        'video': video,
                        'error': '视频文件上传失败，请重试。'
                    })

            # 处理新封面图上传
            if thumbnail_file:
                ext = thumbnail_file.name.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png']:
                    logger.warning(f"封面图格式不支持: 文件='{thumbnail_file.name}', 用户='{username}', IP={ip}")
                    return render(request, 'videos/admin_video_edit.html', {
                        'video': video,
                        'error': '仅支持 JPG 或 PNG 格式的封面图片。'
                    })

                current_time = datetime.now().strftime('%Y%m%d%H%M%S')
                clean_title = slugify(title)
                thumbnail_filename = f"{current_time}-{clean_title}.{ext}"
                thumbnail_save_path = os.path.join(
                    settings.MEDIA_ROOT, 'thumbnails', 'videohosting_videos', thumbnail_filename
                )

                os.makedirs(os.path.dirname(thumbnail_save_path), exist_ok=True)

                try:
                    with open(thumbnail_save_path, 'wb+') as destination:
                        for chunk in thumbnail_file.chunks():
                            destination.write(chunk)

                    # 删除旧封面文件（可选）
                    if old_thumbnail_url:
                        old_thumb_path = old_thumbnail_url.replace('/media/', '', 1)
                        old_thumb_full = os.path.join(settings.MEDIA_ROOT, old_thumb_path)
                        if os.path.isfile(old_thumb_full):
                            try:
                                os.remove(old_thumb_full)
                                logger.info(f"旧封面文件已删除: {old_thumbnail_url}, 用户='{username}', IP={ip}")
                            except Exception as e:
                                logger.warning(f"删除旧封面文件失败: {old_thumbnail_url}, 错误={e}")

                    video.thumbnail_url = f"{settings.MEDIA_URL}thumbnails/videohosting_videos/{thumbnail_filename}"
                    logger.info(f"封面图片已更新: 文件='{thumbnail_filename}', 用户='{username}', IP={ip}")
                except Exception as e:
                    logger.error(f"上传封面图片失败: 标题='{title}', 错误={str(e)}, 用户='{username}', IP={ip}")
                    return render(request, 'videos/admin_video_edit.html', {
                        'video': video,
                        'error': '封面图片上传失败，请重试。'
                    })

            # 保存数据库
            try:
                video.save()
                logger.info(f"视频修改成功: 视频ID={video.id}, 标题='{video.title}', 用户='{username}', IP={ip}")
            except Exception as e:
                logger.error(f"保存视频到数据库失败 (修改): 视频ID={video.id}, 错误={str(e)}, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'video': video,
                    'error': '保存失败，请重试。'
                })

        else:
            # ========== 新增视频 ==========
            logger.info(f"管理员开始新增视频: 提交标题='{title}', 用户='{username}', IP={ip}")

            if not video_file:
                logger.warning(f"新增视频失败: 未上传视频文件, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '请上传视频文件。'
                })
            if not thumbnail_file:
                logger.warning(f"新增视频失败: 未上传封面图片, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '请上传封面图片。'
                })

            ext = thumbnail_file.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                logger.warning(f"新增视频失败: 封面图格式不支持, 文件='{thumbnail_file.name}', 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '封面图片仅支持 JPG 或 PNG 格式。'
                })

            current_time = datetime.now().strftime('%Y%m%d%H%M%S')
            clean_title = slugify(title)

            # 保存视频文件
            video_filename = f"{current_time}-{clean_title}.mp4"
            video_save_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_filename)
            os.makedirs(os.path.dirname(video_save_path), exist_ok=True)

            try:
                with open(video_save_path, 'wb+') as destination:
                    for chunk in video_file.chunks():
                        destination.write(chunk)
                video_url = f"{settings.MEDIA_URL}videos/{video_filename}"
                logger.info(f"新视频文件已保存: 文件='{video_filename}', 用户='{username}', IP={ip}")
            except Exception as e:
                logger.error(f"保存新视频文件失败: 标题='{title}', 错误={str(e)}, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '视频文件保存失败，请重试。'
                })

            # 保存封面图片
            thumbnail_filename = f"{current_time}-{clean_title}.{ext}"
            thumbnail_save_path = os.path.join(
                settings.MEDIA_ROOT, 'thumbnails', 'videohosting_videos', thumbnail_filename
            )
            os.makedirs(os.path.dirname(thumbnail_save_path), exist_ok=True)

            try:
                with open(thumbnail_save_path, 'wb+') as destination:
                    for chunk in thumbnail_file.chunks():
                        destination.write(chunk)
                thumbnail_url = f"{settings.MEDIA_URL}thumbnails/videohosting_videos/{thumbnail_filename}"
                logger.info(f"新封面图片已保存: 文件='{thumbnail_filename}', 用户='{username}', IP={ip}")
            except Exception as e:
                logger.error(f"保存新封面图片失败: 标题='{title}', 错误={str(e)}, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '封面图片保存失败，请重试。'
                })

            # 创建数据库记录
            try:
                Video.objects.create(
                    title=title,
                    video_url=video_url,
                    thumbnail_url=thumbnail_url
                )
                logger.info(f"新视频创建成功: 标题='{title}', 用户='{username}', IP={ip}")
            except Exception as e:
                logger.error(f"创建新视频数据库记录失败: 标题='{title}', 错误={str(e)}, 用户='{username}', IP={ip}")
                return render(request, 'videos/admin_video_edit.html', {
                    'error': '数据库保存失败，请重试。'
                })

        return redirect('admin_dashboard')

    context = {
        'video': video
    }
    return render(request, 'videos/admin_video_edit.html', context)
