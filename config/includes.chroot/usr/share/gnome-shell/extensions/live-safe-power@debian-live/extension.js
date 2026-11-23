import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class SafePower extends Extension {
    enable() {
        this._dialog = Main.endSessionDialog;
        this._original = this._dialog._confirm;
        const extension = this;
        this._dialog._confirm = async function(signal) {
            if (!['ConfirmedShutdown', 'ConfirmedReboot'].includes(signal))
                return extension._original.call(this, signal);
            if (extension._busy)
                return;
            extension._busy = true;
            this.cancel();
            Main.notify('암호화 볼륨 확인 중', 'VeraCrypt 볼륨을 해제한 뒤 종료합니다.');
            const operation = signal === 'ConfirmedReboot' ? 'reboot' : 'poweroff';
            try {
                const [ok, message] = await new Promise((resolve, reject) => {
                    Gio.DBus.system.call('org.debianlive.SafePower', '/org/debianlive/SafePower',
                        'org.debianlive.SafePower', 'Request', new GLib.Variant('(s)', [operation]),
                        new GLib.VariantType('(bs)'), Gio.DBusCallFlags.NONE, 180000, null,
                        (connection, result) => {
                            try { resolve(connection.call_finish(result).deepUnpack()); }
                            catch (error) { reject(error); }
                        });
                });
                if (!ok)
                    Main.notifyError('종료 취소', message);
            } catch (error) {
                Main.notifyError('종료 취소', `종료 보호 서비스에 연결하지 못했습니다: ${error.message}`);
            } finally {
                extension._busy = false;
            }
        };
    }
    disable() {
        if (this._dialog && this._original)
            this._dialog._confirm = this._original;
        this._dialog = null;
    }
}
