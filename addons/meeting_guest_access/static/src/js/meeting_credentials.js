import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
import { onMounted, onWillUnmount, reactive, useState } from '@odoo/owl';
import { Store } from '@mail/core/common/store_service';
import { ChannelInvitation } from '@mail/discuss/core/common/channel_invitation';

patch(Store.prototype, {
    async startMeeting() {
        this.meetingCredentialsByThreadId ||= reactive({});
        await super.startMeeting(...arguments);
        const thread = this.openInviteThread;
        if (!thread?.id) return;
        const credentials = await rpc('/meeting/credentials', { channel_id: thread.id });
        credentials.channel_id = thread.id;
        this.meetingCredentialsByThreadId[thread.id] = credentials;
    },
});

patch(ChannelInvitation.prototype, {
    setup(...args) {
        super.setup(...args);
        this.meetingCredentialsByThreadId = this.store.meetingCredentialsByThreadId || {};
        this.pendingGuests = useState([]);
        this.pendingGuestsTimer = undefined;
        onMounted(() => {
            this.refreshPending();
            this.pendingGuestsTimer = window.setInterval(() => this.refreshPending(), 2000);
        });
        onWillUnmount(() => window.clearInterval(this.pendingGuestsTimer));
    },
    async copyMeetingCredential(value, label) {
        await navigator.clipboard.writeText(value);
        this.notification.add(`${label} copied!`, { type: 'success' });
    },
    async closeMeeting() {
        try {
            await this.orm.call('discuss.channel', 'action_pause_meeting_admission', [[this.props.thread.id]]);
        } catch (error) {
            // Keep meetings usable while an already-running Odoo worker still
            // has the previous registry without the new model method.
            const message = error?.message || String(error);
            if (!message.includes('action_pause_meeting_admission')) throw error;
            await rpc('/meeting/close', { channel_id: this.props.thread.id });
        }
        this.meetingCredentialsByThreadId[this.props.thread.id].open = false;
        this.notification.add('New guest joins are paused. Existing participants remain connected.', { type: 'warning' });
    },
    async refreshPending() {
        const credentials = this.meetingCredentialsByThreadId[this.props.thread.id];
        if (credentials) {
            this.pendingGuests.splice(0, this.pendingGuests.length, ...(await rpc('/meeting/pending', { channel_id: this.props.thread.id })));
        }
    },
    async openMeeting() {
        try {
            await this.orm.call('discuss.channel', 'action_open_meeting', [[this.props.thread.id]]);
        } catch (error) {
            // Compatibility fallback for workers that need a restart before
            // the Python registry contains the new public model method.
            const message = error?.message || String(error);
            if (!message.includes('action_open_meeting')) throw error;
            await rpc('/meeting/open', { channel_id: this.props.thread.id });
        }
        this.meetingCredentialsByThreadId[this.props.thread.id].open = true;
        this.notification.add('Meeting is open. Admit guests as they arrive.', { type: 'success' });
        await this.refreshPending();
    },
    async admitGuest(memberId) {
        await rpc('/meeting/admit', { channel_id: this.props.thread.id, member_id: memberId });
        await this.refreshPending();
    },
});
