import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from read_only_mode import writeable_site_required

from demoscene.views.generic import AjaxConfirmationView
from forums.forms import NewTopicForm, ReplyForm
from forums.models import Post, Topic


POSTS_PER_PAGE = 50


def index(request):
    topics = Topic.objects.order_by('-last_post_at').select_related('created_by_user', 'last_post_by_user')

    return render(request, 'forums/index.html', {
        'menu_section': 'forums',
        'topics': topics,
    })


@writeable_site_required
@login_required
def new_topic(request):
    if request.POST:
        form = NewTopicForm(request.POST)
        if form.is_valid():
            topic = Topic.objects.create(
                title=form.cleaned_data['title'],
                created_by_user=request.user,
                last_post_at=datetime.datetime.now(),
                last_post_by_user=request.user
            )
            Post.objects.create(user=request.user, topic=topic, body=form.cleaned_data['body'])
            return redirect(topic.get_absolute_url())
    else:
        form = NewTopicForm()

    return render(request, 'forums/new_topic.html', {
        'menu_section': 'forums',
        'form': form,
    })


def topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    posts = topic.posts.order_by('created_at').select_related('user')
    paginator = Paginator(posts, POSTS_PER_PAGE)

    page = request.GET.get('page')
    try:
        posts_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        # If page is not an integer, or out of range (e.g. 9999), deliver last page of results.
        posts_page = paginator.page(paginator.num_pages)

    return render(request, 'forums/topic.html', {
        'menu_section': 'forums',
        'topic': topic,
        'posts': posts_page,
        'form': ReplyForm(),
    })


def post(request, post_id):
    """ topic view but ensuring that we display the page that contains the given post """
    post = get_object_or_404(Post, id=post_id)
    topic = post.topic
    posts = topic.posts.order_by('created_at').select_related('user')

    post_offset = topic.posts.filter(created_at__lt=post.created_at).count()
    paginator = Paginator(posts, POSTS_PER_PAGE)

    page = int(post_offset / POSTS_PER_PAGE) + 1
    posts_page = paginator.page(page)

    return render(request, 'forums/topic.html', {
        'menu_section': 'forums',
        'topic': topic,
        'posts': posts_page,
        'form': ReplyForm(),
    })


@writeable_site_required
@login_required
def topic_reply(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    post = Post(topic=topic, user=request.user)

    if request.POST:
        form = ReplyForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            topic.last_post_at = post.created_at
            topic.last_post_by_user = request.user
            topic.reply_count = topic.posts.count() - 1
            topic.save()
            return redirect(topic.get_absolute_url() + ('#post-%d' % post.id))
        else:
            # the only possible error is leaving the box totally empty.
            # Redirect back to topic page in that case
            return redirect(topic.get_absolute_url())
    else:
        form = ReplyForm(instance=post)

    return render(request, 'forums/add_reply.html', {
        'menu_section': 'forums',
        'topic': topic,
        'form': form,
    })


class DeletePostView(AjaxConfirmationView):
    action_url_path = "forums_delete_post"

    def get_redirect_url(self):
        if Topic.objects.filter(id=self.object.topic.id).exists():
            return self.object.topic.get_absolute_url()
        else:
            return reverse('forums')

    def get_cancel_url(self):
        return self.object.get_absolute_url()

    def get_object(self, request, post_id):
        return Post.objects.get(id=post_id)

    def is_permitted(self):
        return self.request.user.is_staff

    def get_message(self):
        return "Are you sure you want to delete this post?"

    def get_html_title(self):
        return "Deleting forum post"

    def perform_action(self):
        self.object.delete()
        messages.success(self.request, "Post deleted")
