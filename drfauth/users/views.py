from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse, reverse_lazy
import easyocr
from django.views import View

from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, CommentForm, checkimage, UserChatForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from .models import Post, Comment, checkmk, Profile, FriendRequest, UserChat
from django.db.models import Count
from django.utils.datastructures import MultiValueDictKeyError
from .filters import PostFilter
from PIL import Image
import cv2
from django.core.mail import send_mail
import os

from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView, FormView
)
from django.contrib.auth.models import User, AbstractUser
from django.contrib import messages


@login_required
def post_detail(request, pk):
    post = Post.objects.get(id=pk)
    ied = pk
    comments = Comment.objects.filter(post=post).order_by("-pk")

    is_liked = False
    if post.likes.filter(id=request.user.id).exists():
        is_liked = True
    else:
        is_liked = False

    is_favorite = False
    if post.favorites.filter(id=request.user.id).exists():
        is_favorite = True
    else:
        is_favorite = False

    if request.method == 'POST':
        cf = CommentForm(request.POST or None)
        if cf.is_valid():
            content = request.POST.get('content')
            comment = Comment.objects.create(post=post, user=request.user, content=content)
            comment.save()
            return redirect(post.get_absolute_url())
    else:
        cf = CommentForm()

    context = {
        'title': 'Post Details',
        'comments': comments,
        'ied': ied,
        'object': post,
        'is_favorite': is_favorite,
        'is_liked': is_liked,
        'total_likes': post.likecount(),
        'comment_form': cf,
        'friend_requests': FriendRequest.objects.filter(
            sender=request.user
        ).values_list('receiver_id', flat=True)
    }
    return render(request, 'users/post_detail.html', context)


@login_required
def favorite(request, id):
    post = get_object_or_404(Post, id=id)
    if post.favorites.filter(id=request.user.id).exists():
        messages.success(request, f'bookmark removed !')
        post.favorites.remove(request.user)
    else:
        post.favorites.add(request.user)
        messages.success(request, f'Post Saved! You can check it out in your Bookmarks.')
    return HttpResponseRedirect(post.get_absolute_url())


@login_required
def favorite_list(request):
    user = request.user
    post = user.favorites.all()
    context = {
        'post': post,
        'title': 'Bookmarks'
    }
    return render(request, 'users/bookmark.html', context)


@login_required
def postlike(request):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=request.POST.get('post_id'))
        is_liked = False
        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            is_liked = False
        else:
            post.likes.add(request.user)
            # notify.send(request.user, recipient=post.author, actor=request.user,
            #     verb='liked your post', nf_type='liked_post')
            is_liked = True

        return HttpResponseRedirect(post.get_absolute_url())


@login_required
def deletecomment(request, id):
    comment = get_object_or_404(Comment, id=id)
    comment.delete()
    messages.success(request, f'Comment deleted!')
    return redirect(comment.post.get_absolute_url())


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'users/feed.html'
    context_object_name = "posts"
    ordering = ['-date_posted']

    def get_context_data(self, *args, **kwargs):
        context = super(PostListView, self).get_context_data(*args, **kwargs)
        context["title"] = 'Newsfeed'
        context["friend_requests"] = self.request.user.sent_requests.all().values_list('receiver_id', flat=True)
        context["accepted_data"] = self.request.user.sent_requests.filter(is_accepted=True).values_list('receiver_id', flat=True)
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['image', 'title', 'caption', 'link']
    success_url = '/dashboard'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['image', 'title', 'caption', 'link']
    success_url = '/dashboard'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/dashboard'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


@login_required
def delete_user(request):
    context = {
        'title': 'Deactivate Account'
    }
    return render(request, 'users/deactivate.html', context)


@login_required
def delete_user_confirm(request):
    context = {}
    if request.user.is_authenticated:
        username = request.user.username
    try:
        u = User.objects.get(username=username)
        u.delete()
        context['msg'] = 'The user is deleted.'
    except User.DoesNotExist:
        context['msg'] = 'User does not exist.'
    except Exception as e:
        context['msg'] = e.message

    messages.success(request, f' {username} account is deleted !')
    return redirect('socio-home')


def signup(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username} !')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/signup.html', {'form': form, 'title': 'Sign up to socio'})


@login_required
def filter_list(request):
    f = PostFilter(request.GET, queryset=Post.objects.all().order_by('-date_posted'))
    return render(request, 'users/filtered.html',
                  {'filter': f, 'title': 'Search Post in Socio', 'friend_requests': FriendRequest.objects.filter(
                      sender=request.user
                  ).values_list('receiver_id', flat=True)})


def home(request):
    context = {
        'title': 'Socio Home',

    }
    return render(request, 'users/home.html', context)


##############################################################################


# Assuming your form is named 'checkimage'


def document(request):
    text = None  # Initialize text variable

    if request.method == 'POST':
        # Process the form submission
        form = checkimage(request.POST, request.FILES)

        if form.is_valid():
            # Save the uploaded file
            uploaded_file = form.save(commit=False)
            uploaded_file.d_image = request.FILES['d_image']
            uploaded_file.save()

            # Get the path of the uploaded image
            imgname = form.cleaned_data.get('d_image')
            full_path = os.path.join(default_storage.location, 'detected', str(imgname))

            try:
                # Ensure the uploaded file exists
                if not os.path.exists(full_path):
                    raise ValueError("The uploaded file does not exist.")

                # Initialize EasyOCR reader
                reader = easyocr.Reader(['en'])  # 'en' for English; add more languages as needed

                # Perform OCR using EasyOCR
                text_result = reader.readtext(full_path, detail=0)  # `detail=0` returns plain text
                text = "\n".join(text_result)  # Combine detected text into a single string
                print("Extracted text:", text)

            except Exception as e:
                # Handle any errors during the OCR process
                print(f"Error processing image with EasyOCR: {e}")
                text = "Error: Unable to process the uploaded image using EasyOCR."

        else:
            # Handle invalid form submission
            text = "Error: Invalid form submission."

    else:
        # If it's a GET request, initialize the form
        form = checkimage()

    # Prepare the context for rendering the template
    context = {
        'title': 'Document OCR',
        'form': form,
        'data': text,
    }

    return render(request, 'users/fileupload.html', context)


################################################################################
@login_required
def trending(request):
    post = Post.objects.annotate(like_count=Count('likes')).order_by('-like_count', '-date_posted')
    context = {
        'title': 'Trending',
        'posts': post,
    }
    return render(request, 'users/trending.html', context)


@login_required
def dashboard(request):
    logged_in_user = request.user
    logged_in_user_posts = Post.objects.filter(author=logged_in_user).order_by('-date_posted')
    cnt = logged_in_user_posts.count()
    context = {
        'title': 'DashBoard',
        'posts': logged_in_user_posts,
        'count': cnt
    }
    return render(request, 'users/dashboard.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        uform = UserUpdateForm(request.POST, instance=request.user)

        # Attempt to get or create the profile
        profile, created = Profile.objects.get_or_create(user=request.user)

        # Update the profile with the uploaded file if it exists
        if request.FILES.get('profile_image'):
            profile.profile_image = request.FILES['profile_image']
            profile.save()

        # pform = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if uform.is_valid():
            uform.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('socio-profile')  # Redirect to avoid resubmitting the form on refresh

    else:
        uform = UserUpdateForm(instance=request.user)

        # Attempt to get the profile or create a new one if not found
        profile, created = Profile.objects.get_or_create(user=request.user)
        pform = ProfileUpdateForm(instance=profile)
    user = get_object_or_404(User, pk=request.user.pk)
    friends = User.objects.filter(
        sent_requests__receiver=user,
        sent_requests__is_accepted=False,
        sent_requests__sender_request=True
    ) | User.objects.filter(
        received_requests__sender=user,
        received_requests__is_accepted=True
    )
    followers = User.objects.filter(
        received_requests__receiver=user,
        received_requests__is_accepted=True
    )

    context = {
        'uform': uform,
        'pform': pform,
        'profile': profile.profile_image,
        'friends_count': friends.count(),
        'following_count': user.sent_requests.filter(is_accepted=True).count() if user.sent_requests.filter(
            is_accepted=True).exists() else user.sent_requests.filter(is_accepted=False).count(),
        'followers_count': user.received_requests.filter(receiver=user,
                                                         sender_request=True).count() if user.received_requests.filter(
            is_accepted=True).exists() else user.received_requests.filter(receiver=user, sender_request=False).count(),
    }

    return render(request, 'users/profile.html', context)


# from notify.signals import notify
# class PostDetailView(LoginRequiredMixin,DetailView):
#     model = Post
#     def get_context_data(self, *args, **kwargs):
#         context = super(PostDetailView, self).get_context_data(*args, **kwargs)
#         context["title"] = 'Post Details'
#         return context

class CustomLogout(View):

    def get(self, request):
        logout(request)
        return HttpResponseRedirect(reverse('login'))


class FriendRequestCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        receiver_id = request.POST.get('receiver_id')
        try:
            receiver = User.objects.get(id=receiver_id)
            # Check if a friend request already exists
            if not FriendRequest.objects.filter(sender=request.user, receiver=receiver).exists():
                FriendRequest.objects.create(sender=request.user, receiver=receiver, sender_request=True)
                messages.success(request, 'Friend request sent!')
            else:
                messages.info(request, 'You already sent a friend request to this user.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        return redirect(request.META.get('HTTP_REFERER', 'home'))


class FriendRequestActionView(LoginRequiredMixin, View):
    def post(self, request, request_id):
        action = request.POST.get('action')
        friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)

        if action == 'accept':
            friend_request.is_accepted = True
            friend_request.save()

            # Optionally add friends to each other's profiles
            # request.user.profile.friends.add(friend_request.sender.profile)
            # friend_request.sender.profile.friends.add(request.user.profile)

            messages.success(request, "Friend request accepted.")
        elif action == 'decline':
            friend_request.delete()
            messages.info(request, "Friend request declined.")

        return redirect('socio-profile')


class FollowingListView(LoginRequiredMixin, ListView):
    model = FriendRequest
    template_name = "users/following_list.html"
    context_object_name = "friends"

    def get_queryset(self):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        if user.sent_requests.filter(sender_request=True).exists():
            return FriendRequest.objects.filter(sender=user, is_accepted=True, sender_request=True)
        return FriendRequest.objects.filter(sender=user, is_accepted=False, sender_request=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'following'
        image_pro = Profile.objects.get(user=self.request.user)
        context['friend_requests'] = image_pro.profile_image
        return context


class FollowersListView(LoginRequiredMixin, ListView):
    model = FriendRequest
    template_name = "users/following_list.html"
    context_object_name = "friends"

    def get_queryset(self):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        print(self.kwargs['user_id'])
        if user.received_requests.filter(receiver=user, sender_request=True).exists():
            print("enter=========")
            return FriendRequest.objects.filter(receiver=user, is_accepted=True, sender_request=True)
        return FriendRequest.objects.filter(receiver=user, is_accepted=False, sender_request=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'followers'
        image_pro = Profile.objects.get(user=self.request.user)
        context['friend_requests'] = image_pro.profile_image
        return context


class FriendRequestListView(LoginRequiredMixin, ListView):
    model = FriendRequest
    template_name = "users/following_list.html"
    context_object_name = "friends"

    def get_queryset(self):
        user = get_object_or_404(User, id=self.kwargs['user_id'])
        return FriendRequest.objects.filter(receiver=user, is_accepted=False, sender_request=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'friends'
        image_pro = Profile.objects.get(user=self.request.user)
        context['friend_requests'] = image_pro.profile_image
        return context


class UserListView(LoginRequiredMixin, ListView):
    template_name = 'users/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        # Exclude the current user from the list
        return User.objects.exclude(id=self.request.user.id)

class ChatView(LoginRequiredMixin, FormView):
    template_name = 'users/chat.html'
    form_class = UserChatForm

    def get_success_url(self):
        # Redirect to the same chat page after sending a message
        return reverse_lazy('chat-view', kwargs={'user_id': self.kwargs['user_id']})

    def form_valid(self, form):
        # Save the chat message
        chat = form.save(commit=False)
        chat.sender = self.request.user
        chat.receiver = get_object_or_404(User, id=self.kwargs['user_id'])
        chat.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        # Fetch chat messages between the current user and the selected user
        context = super().get_context_data(**kwargs)
        receiver = get_object_or_404(User, id=self.kwargs['user_id'])
        context['receiver'] = receiver
        context['chats'] = UserChat.objects.filter(
            sender=self.request.user, receiver=receiver
        ) | UserChat.objects.filter(
            sender=receiver, receiver=self.request.user
        ).order_by('-created_ts')
        return context



