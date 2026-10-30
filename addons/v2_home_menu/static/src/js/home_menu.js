/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { fuzzyLookup } from "@web/core/utils/search";

class V2HomeMenu extends Component {
    static template = "v2_home_menu.HomeMenu";
    static props = {};

    setup() {
        this.action = useService("action");
        this.menus = useService("menu");
        this.searchRef = useRef("searchInput");

        this.state = useState({
            searchValue: "",
            searchResults: [],
            isSearchOpen: false,
            currentTime: this._getTime(),
            currentDate: this._getDate(),
            greeting: this._getGreeting(),
        });

        this._clockInterval = null;

        onMounted(() => {
            this._clockInterval = setInterval(() => {
                this.state.currentTime = this._getTime();
                this.state.currentDate = this._getDate();
                this.state.greeting = this._getGreeting();
            }, 1000);
        });

        onWillUnmount(() => {
            if (this._clockInterval) {
                clearInterval(this._clockInterval);
            }
        });
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get apps() {
        const menuTree = this.menus.getMenuAsTree("root");
        const { apps } = computeAppsAndMenuItems(menuTree);
        return apps;
    }

    get filteredApps() {
        if (!this.state.searchValue) {
            return this.apps;
        }
        return fuzzyLookup(this.state.searchValue, this.apps, (a) => a.label);
    }

    get allMenuItems() {
        const menuTree = this.menus.getMenuAsTree("root");
        const { menuItems } = computeAppsAndMenuItems(menuTree);
        return menuItems;
    }

    // -------------------------------------------------------------------------
    // Clock helpers
    // -------------------------------------------------------------------------

    _getTime() {
        const now = new Date();
        return now.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
        });
    }

    _getDate() {
        return new Date().toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    _getGreeting() {
        const h = new Date().getHours();
        if (h < 12) return "Good Morning";
        if (h < 17) return "Good Afternoon";
        return "Good Evening";
    }

    // -------------------------------------------------------------------------
    // Search
    // -------------------------------------------------------------------------

    onSearchInput(ev) {
        const val = ev.target.value;
        this.state.searchValue = val;
        if (val.trim()) {
            const appMatches = fuzzyLookup(val, this.apps, (a) => a.label).map((a) => ({
                ...a,
                type: "app",
            }));
            const menuMatches = fuzzyLookup(val, this.allMenuItems, (m) => m.label)
                .slice(0, 8)
                .map((m) => ({ ...m, type: "menu" }));
            this.state.searchResults = [...appMatches, ...menuMatches].slice(0, 10);
            this.state.isSearchOpen = this.state.searchResults.length > 0;
        } else {
            this.state.searchResults = [];
            this.state.isSearchOpen = false;
        }
    }

    onSearchBlur() {
        // Delay so click on result registers first
        setTimeout(() => {
            this.state.isSearchOpen = false;
        }, 200);
    }

    onSearchFocus() {
        if (this.state.searchValue && this.state.searchResults.length) {
            this.state.isSearchOpen = true;
        }
    }

    clearSearch() {
        this.state.searchValue = "";
        this.state.searchResults = [];
        this.state.isSearchOpen = false;
        if (this.searchRef.el) {
            this.searchRef.el.focus();
        }
    }

    // -------------------------------------------------------------------------
    // Navigation
    // -------------------------------------------------------------------------

    openApp(app) {
        this.menus.selectMenu(app);
        this.action.doAction(app.actionID, { clearBreadcrumbs: true });
    }

    openSearchResult(result) {
        this.state.isSearchOpen = false;
        this.state.searchValue = "";
        this.action.doAction(result.actionID, { clearBreadcrumbs: true });
    }

    // -------------------------------------------------------------------------
    // App icon helpers
    // -------------------------------------------------------------------------

    getAppStyle(app) {
        if (app.webIcon && app.webIcon.backgroundColor) {
            return `background: ${app.webIcon.backgroundColor};`;
        }
        return "";
    }

    getIconClass(app) {
        if (app.webIcon && app.webIcon.iconClass) {
            return app.webIcon.iconClass;
        }
        return "fa fa-th-large";
    }

    getIconColor(app) {
        if (app.webIcon && app.webIcon.color) {
            return `color: ${app.webIcon.color};`;
        }
        return "color: #ffffff;";
    }
}

registry.category("actions").add("v2_home_menu.HomeMenu", V2HomeMenu);
