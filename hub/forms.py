from django import forms

from .models import Message, Project, Task, Thread


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description"]


class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["parent"].queryset = Task.objects.filter(project=project)

    class Meta:
        model = Task
        fields = ["title", "description", "status", "priority", "parent", "position", "due_at", "tags"]
        widgets = {
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ["title", "kind"]


class MessageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["author_role"].initial = "human"

    class Meta:
        model = Message
        fields = ["body", "author_label", "author_role"]
        widgets = {
            "author_role": forms.HiddenInput(),
        }
