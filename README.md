
## 安装说明
1. 请确保您的电脑有以下环境：python3
2. 在想要安装的文件夹下解压video_hosting.zip，双击进入video_hosting文件夹
3. 在该目录下进入cmd，输入指令“pip install -r requirement.txt”,安装需要的python库（ps:这个文件有冗余，也可以自己缺啥装啥）
4.  创建管理员账号(命令行运行)  
python manage.py createsuperuser  
Username: root000（自行修改）  
Email: （可空）  
Password: root000（自行修改）  
Password (again): root000
5. 在根目录下打开cmd界面，输入指令“python manage.py runserver”
6. 打开浏览器，进入http://127.0.0.1:8000/videohosting/admin-login/，输入步骤四创建的管理员账号即可使用
