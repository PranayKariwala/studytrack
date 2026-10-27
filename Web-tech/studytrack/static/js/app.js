/**
 * StudyTrack Client-side JavaScript
 * - CSRF token helper for fetch requests
 * - Progressive AJAX toggle for assignment completion
 * - Delete confirmation modal/prompt assistance
 * - Auto-dismiss notifications
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Get CSRF token from document cookies or form input
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrftoken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

  // 2. Progressive Enhancement: AJAX toggle for assignment completion
  const ajaxToggleButtons = document.querySelectorAll('.btn-ajax-toggle-status');
  ajaxToggleButtons.forEach(button => {
    button.addEventListener('click', async function (e) {
      e.preventDefault();
      const form = this.closest('form');
      if (!form) return;

      const url = form.getAttribute('action');
      const assignmentRow = this.closest('tr') || document.getElementById(`assignment-card-${this.dataset.assignmentId}`);

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            // Update button UI
            if (data.is_completed) {
              this.classList.remove('btn-outline-success');
              this.classList.add('btn-success');
              this.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Completed';
              if (assignmentRow) {
                assignmentRow.classList.add('assignment-completed');
                const badge = assignmentRow.querySelector('.status-badge');
                if (badge) {
                  badge.className = 'badge badge-status-completed status-badge';
                  badge.innerHTML = '<i class="bi bi-check2-circle me-1"></i> Completed';
                }
              }
            } else {
              this.classList.remove('btn-success');
              this.classList.add('btn-outline-success');
              this.innerHTML = '<i class="bi bi-circle me-1"></i> Mark Done';
              if (assignmentRow) {
                assignmentRow.classList.remove('assignment-completed');
                const badge = assignmentRow.querySelector('.status-badge');
                if (badge) {
                  if (data.is_overdue) {
                    badge.className = 'badge badge-status-overdue status-badge';
                    badge.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i> Overdue';
                  } else {
                    badge.className = 'badge badge-status-pending status-badge';
                    badge.innerHTML = '<i class="bi bi-clock me-1"></i> Pending';
                  }
                }
              }
            }
          }
        } else {
          // Fallback: Submit form traditionally if fetch failed
          form.submit();
        }
      } catch (err) {
        console.warn('AJAX toggle failed; falling back to traditional form submit.', err);
        form.submit();
      }
    });
  });

  // 3. Confirm Delete Prompts
  const deleteForms = document.querySelectorAll('form.confirm-delete-form');
  deleteForms.forEach(form => {
    form.addEventListener('submit', function (e) {
      const itemName = this.dataset.itemName || 'this item';
      if (!confirm(`Are you sure you want to permanently delete "${itemName}"? This action cannot be undone.`)) {
        e.preventDefault();
      }
    });
  });

  // 4. Auto-dismiss alerts after 5 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(alert => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    });
  }, 5000);
});
