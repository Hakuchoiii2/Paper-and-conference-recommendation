const USER_ID_KEY = 'facetrec_explore_user_id';
export const PROFILE_UPDATED_EVENT = 'facetrec-profile-updated';

export function getExploreUserId(): string {
  let uid = localStorage.getItem(USER_ID_KEY);
  if (!uid) {
    uid = `user_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(USER_ID_KEY, uid);
  }
  return uid;
}

export function notifyProfileUpdated(paperCount?: number): void {
  window.dispatchEvent(
    new CustomEvent(PROFILE_UPDATED_EVENT, { detail: { paperCount } })
  );
}
