import json
import logging
import os
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException
from .database import db_session, SessionLocal
from .models import PushSubscription, Team, User
from .security import current_user

router = APIRouter(prefix='/api/push')


def enabled():
    return all(os.getenv(key) for key in ('VAPID_PRIVATE_KEY', 'VAPID_PUBLIC_KEY', 'VAPID_SUBJECT'))


@router.get('/config')
def config(user: User = Depends(current_user)):
    return {'enabled': enabled(), 'public_key': os.getenv('VAPID_PUBLIC_KEY') if enabled() else None}


class SubscriptionInput(BaseModel):
    endpoint: str = Field(max_length=2048)
    keys: dict[str, str]


@router.post('/subscriptions')
def subscribe(payload: SubscriptionInput, user: User = Depends(current_user), db: Session = Depends(db_session)):
    if not enabled(): raise HTTPException(503, 'Telefoonmeldingen zijn nog niet ingesteld door de beheerder.')
    if not user.team_id: raise HTTPException(403, 'Join a team first')
    url = urlparse(payload.endpoint)
    host = url.hostname or ''
    allowed = ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'push.apple.com', 'notify.windows.com')
    if url.scheme != 'https' or url.port not in (None, 443) or url.username or not any(host == domain or host.endswith('.' + domain) for domain in allowed):
        raise HTTPException(422, 'Unsupported push service')
    if set(payload.keys) != {'p256dh', 'auth'} or any(not value or len(value) > 256 for value in payload.keys.values()):
        raise HTTPException(422, 'Invalid subscription keys')
    row = db.query(PushSubscription).filter_by(endpoint=payload.endpoint).first()
    if row is None: row = PushSubscription(endpoint=payload.endpoint); db.add(row)
    row.user_id = user.id; row.keys_json = json.dumps(payload.keys)
    db.commit()
    return {'ok': True}


@router.delete('/subscriptions')
def unsubscribe(user: User = Depends(current_user), db: Session = Depends(db_session)):
    db.query(PushSubscription).filter_by(user_id=user.id).delete()
    db.commit()
    return {'ok': True}


def notify_capture(game_id, point_name, team_name):
    if not enabled(): return
    with SessionLocal() as db:
        subscriptions = db.query(PushSubscription).join(User, User.id == PushSubscription.user_id).join(Team, Team.id == User.team_id).filter(Team.game_id == game_id, User.active.is_(True)).all()
        for row in subscriptions:
            try:
                webpush(subscription_info={'endpoint': row.endpoint, 'keys': json.loads(row.keys_json)}, data=json.dumps({'title': 'Vlag veroverd!', 'body': f'{team_name} heeft {point_name} veroverd.', 'url': '/'}), vapid_private_key=os.environ['VAPID_PRIVATE_KEY'], vapid_claims={'sub': os.environ['VAPID_SUBJECT']}, ttl=300, timeout=10)
            except WebPushException as exc:
                if exc.response is not None and exc.response.status_code in (404, 410): db.delete(row)
                else: logging.warning('Capture push delivery failed for subscription %s', row.id)
            except Exception:
                logging.warning('Capture push configuration/delivery failed for subscription %s', row.id)
        db.commit()
