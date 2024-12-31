from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from PIL import Image
from django.urls import reverse


# # Create your models here.

class Post(models.Model):
    image = models.ImageField(default="default_foo.png", upload_to="post_picture")
    title = models.CharField(max_length=100)
    caption = models.TextField()
    link = models.URLField(blank=True, default="")
    likes = models.ManyToManyField(User, related_name='likes', blank=True)
    favorites = models.ManyToManyField(User, related_name='favorites', blank=True)
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.author.username}\'s Post- {self.title}'

    def likecount(self):
        return self.likes.count()

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.image.path)
        if img.height > 400 or img.width > 400:
            # output_size = (300, 300)
            # img.thumbnail(output_size)
            im = img.resize((400, 400))
            im.save(self.image.path)
        elif img.height < 400 or img.width < 400:
            im = img.resize((400, 400))
            im.save(self.image.path)


class Profile(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='profiles_user')
    profile_image = models.ImageField(upload_to="profile_pics", null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.profile_image:
            img = Image.open(self.profile_image.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_image.path)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'comment on {} by {}'.format(self.post.title, self.user.username)


class checkmk(models.Model):
    mid = models.AutoField(primary_key=True)
    d_image = models.ImageField(upload_to="detected")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.d_image.path)
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.d_image.path)

    def road(self):
        return self.d_image.path

class FriendRequest(models.Model):
    sender = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    sender_request = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.sender} -> {self.receiver}'

    class Meta:
        db_table = "friend_request"


class UserChat(models.Model):
    sender = models.ForeignKey(User, related_name='sender_chats', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='receiver_chats', on_delete=models.CASCADE)
    message = models.TextField()
    created_ts = models.DateTimeField(auto_now_add=True)
