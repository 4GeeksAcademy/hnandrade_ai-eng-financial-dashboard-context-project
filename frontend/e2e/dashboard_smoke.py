#!/usr/bin/env python3
"""
Financial Dashboard Smoke Test - Accessibility & Performance Verification.
Verifies a11y and performance changes via Playwright browser automation.
Run with: python frontend/e2e/dashboard_smoke.py
"""

import sys
import re
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5173"
API_METRICS_PATH = "/api/metrics"

def print_check(check_name, status, evidence=""):
    """Print a table row for each check."""
    status_icon = "✅" if status else "❌"
    print(f"| {status_icon} {check_name:<40} | {status!s:<8} | {evidence[:80]}")
    return status

def new_page(browser, reduced_motion=None):
    """Create a fresh page with console/error listeners and CLS observer.
    
    Requires Playwright in a venv. Run with:
    python frontend/e2e/dashboard_smoke.py
    """
    page = browser.new_page()
    
    # Register console and pageerror listeners
    page.on("console", lambda msg: None)
    page.on("pageerror", lambda exc: None)
    
    # Add CLS observer BEFORE any navigation
    page.add_init_script("""
        window.clsValue = 0;
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                    window.clsValue += entry.value;
                }
            }
        });
        observer.observe({type: 'layout-shift', buffered: true});
    """)
    
    # Apply reduced motion if requested
    if reduced_motion:
        page.emulate_media(reduced_motion=reduced_motion)
    
    return page


def run_tests():
    """Execute all accessibility and performance checks."""
    print("\n" + "="*140)
    print("FINANCIAL DASHBOARD SMOKE TEST")
    print("="*140)
    print("| Check                                    | Result   | Evidence")
    print("|" + "-"*138 + "|")
    
    all_passed = True
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ===== CHECK A: Carga (Título, Meta Description, Errores) =====
        page_a = new_page(browser)
        
        console_errors = []
        page_errors = []
        
        def on_console(msg):
            if msg.type in ("error", "warning"):
                console_errors.append(f"{msg.type}: {msg.text}")
        
        def on_page_error(exc):
            page_errors.append(str(exc))
        
        page_a.on("console", on_console)
        page_a.on("pageerror", on_page_error)
        
        # Collect network requests for lazy-loading check
        network_requests = []
        def on_response(response):
            network_requests.append(response.url)
        page_a.on("response", on_response)
        
        # Navigate to app
        page_a.goto(BASE_URL)
        page_a.wait_for_load_state("networkidle")
        
        title = page_a.title()
        check_a1 = print_check(
            "A.1 - Title == 'Financial Overview'",
            title == "Financial Overview",
            f"Found: '{title}'"
        )
        all_passed &= check_a1
        
        # Check meta description
        meta_desc = page_a.locator("meta[name='description']").get_attribute("content")
        check_a2 = print_check(
            "A.2 - Meta description present",
            meta_desc is not None and len(meta_desc) > 0,
            f"Content: '{meta_desc[:60]}...'" if meta_desc else "Not found"
        )
        all_passed &= check_a2
        
        # Check console/page errors
        check_a3 = print_check(
            "A.3 - Zero console errors",
            len(console_errors) == 0,
            f"Count: {len(console_errors)}" + (f" ({console_errors[0][:50]}...)" if console_errors else "")
        )
        all_passed &= check_a3
        
        check_a4 = print_check(
            "A.4 - Zero page errors",
            len(page_errors) == 0,
            f"Count: {len(page_errors)}" + (f" ({page_errors[0][:50]}...)" if page_errors else "")
        )
        all_passed &= check_a4
        
        # ===== CHECK B: Lazy Loading (Income/Profit Charts) =====
        income_urls = [u for u in network_requests if "income-outcome-chart" in u]
        profit_urls = [u for u in network_requests if "profit-percent-chart" in u]
        
        check_b1 = print_check(
            "B.1 - Income-Outcome chart lazy-loaded",
            len(income_urls) > 0,
            f"Found {len(income_urls)} request(s)"
        )
        all_passed &= check_b1
        
        check_b2 = print_check(
            "B.2 - Profit-Percent chart lazy-loaded",
            len(profit_urls) > 0,
            f"Found {len(profit_urls)} request(s)"
        )
        all_passed &= check_b2
        
        # ===== CHECK C: Semantic HTML =====
        h1_count = page_a.locator("h1").count()
        check_c1 = print_check(
            "C.1 - Exactly 1 h1",
            h1_count == 1,
            f"Found: {h1_count}"
        )
        all_passed &= check_c1
        
        h2_count = page_a.locator("h2").count()
        check_c2 = print_check(
            "C.2 - At least 1 h2",
            h2_count >= 1,
            f"Found: {h2_count}"
        )
        all_passed &= check_c2
        
        # Check for accessible tables with captions per chart
        tables = page_a.locator("table").all()
        captions_found = page_a.locator("table caption").count()
        table_rows_total = page_a.locator("table tbody tr").count()
        
        check_c3 = print_check(
            "C.3 - Tables with captions for charts",
            len(tables) > 0 and captions_found > 0 and table_rows_total > 0,
            f"Tables: {len(tables)}, Captions: {captions_found}, Rows: {table_rows_total}"
        )
        all_passed &= check_c3
        
        # Get accessible names of charts
        charts = page_a.locator("[role='img'], svg[aria-label]").all()
        chart_names = []
        for chart in charts:
            label = chart.get_attribute("aria-label")
            if label:
                chart_names.append(label)
        
        check_c4 = print_check(
            "C.4 - Charts have accessible names",
            len(chart_names) > 0,
            f"Found {len(chart_names)}: {', '.join(chart_names[:2])}"
        )
        all_passed &= check_c4
        
        page_a.close()
        
        # ===== CHECK D: Keyboard Navigation & Focus Visibility =====
        page_d = new_page(browser)
        page_d.goto(BASE_URL)
        page_d.wait_for_load_state("networkidle")
        
        # Precondition: exactly 2 recharts-wrapper elements
        wrappers = page_d.locator(".recharts-wrapper").all()
        if len(wrappers) != 2:
            check_d_pre = print_check(
                "D.Pre - Exactly 2 recharts-wrapper",
                False,
                f"Found {len(wrappers)}, expected 2"
            )
            all_passed = False
        else:
            check_d_pre = print_check(
                "D.Pre - Exactly 2 recharts-wrapper",
                True,
                f"Found {len(wrappers)}"
            )
        
        focus_log = []
        charts_focused = set()
        
        for tab_step in range(20):
            page_d.keyboard.press("Tab")
            page_d.wait_for_timeout(50)
            
            # Get currently focused element info
            focused_info = page_d.evaluate("""() => {
                const elem = document.activeElement;
                if (!elem) return null;
                
                const style = window.getComputedStyle(elem);
                const outline_style = style.outlineStyle || 'none';
                const outline_width = style.outlineWidth || '0px';
                const tabindex = elem.getAttribute('tabindex');
                const ariaLabel = elem.getAttribute('aria-label');
                const tag = elem.tagName;
                const role = elem.getAttribute('role');
                
                // Find which recharts-wrapper contains this element
                let wrapper_idx = -1;
                let current = elem;
                while (current) {
                    const parent = current.closest('.recharts-wrapper');
                    if (parent) {
                        const allWrappers = Array.from(document.querySelectorAll('.recharts-wrapper'));
                        wrapper_idx = allWrappers.indexOf(parent);
                        break;
                    }
                    current = current.parentElement;
                }
                
                return {
                    tag: tag,
                    role: role,
                    aria_label: ariaLabel,
                    tabindex: tabindex,
                    outline_style: outline_style,
                    outline_width: outline_width,
                    wrapper_idx: wrapper_idx,
                    step: """ + str(tab_step) + """
                };
            }""")
            
            if focused_info:
                focus_log.append(focused_info)
                # Print step log
                print(f"  [D Tab {focused_info['step']:2}] {focused_info['tag']:<6} role={focused_info['role']!s:<15} outline-style={focused_info['outline_style']:<10} outline-width={focused_info['outline_width']:<6} wrapper={focused_info['wrapper_idx']}")
                
                if focused_info['wrapper_idx'] >= 0:
                    charts_focused.add(focused_info['wrapper_idx'])
        
        # D.1: Check if focus entered both charts
        check_d1 = print_check(
            "D.1 - Focus enters recharts 0 and 1",
            charts_focused == {0, 1},
            f"Focused charts: {sorted(charts_focused)}"
        )
        all_passed &= check_d1
        
        # D.2: Check outline visibility in focused elements
        outline_visible_in_charts = False
        for log_entry in focus_log:
            if log_entry['wrapper_idx'] >= 0:
                outline_visible = (log_entry['outline_style'] != 'none' and 
                                 log_entry['outline_width'] not in ('0px', '0'))
                if outline_visible:
                    outline_visible_in_charts = True
                    break
        
        check_d2 = print_check(
            "D.2 - Focused element has visible outline",
            outline_visible_in_charts,
            f"Visible outline found: {outline_visible_in_charts}"
        )
        all_passed &= check_d2
        
        # D.3: Test ArrowRight and tooltip changes for each focused chart
        page_d.goto(BASE_URL)
        page_d.wait_for_load_state("networkidle")
        
        has_tooltips = [
            True,  # income-outcome-chart has Tooltip
            True   # profit-percent-chart has Tooltip
        ]
        
        d3_passed_count = 0
        for chart_idx in range(2):
            # Tab to get into chart
            tab_count = 0
            in_chart = False
            while tab_count < 20:
                page_d.keyboard.press("Tab")
                page_d.wait_for_timeout(50)
                
                current_wrapper = page_d.evaluate("""() => {
                    const elem = document.activeElement;
                    let wrapper_idx = -1;
                    let current = elem;
                    while (current) {
                        const parent = current.closest('.recharts-wrapper');
                        if (parent) {
                            const allWrappers = Array.from(document.querySelectorAll('.recharts-wrapper'));
                            wrapper_idx = allWrappers.indexOf(parent);
                            break;
                        }
                        current = current.parentElement;
                    }
                    return wrapper_idx;
                }""")
                
                if current_wrapper == chart_idx:
                    in_chart = True
                    break
                tab_count += 1
            
            if not in_chart or not has_tooltips[chart_idx]:
                status_d3 = "N/A (sin Tooltip)" if not has_tooltips[chart_idx] else "No focus entered"
                print(f"| ❓ D.3.{chart_idx+1} - ArrowRight changes content          | {status_d3:<8} | {status_d3}")
                continue
            
            # Now in chart, get tooltip info BEFORE
            tooltip_before = page_d.evaluate("""() => {
                const wrapper = document.querySelectorAll('.recharts-wrapper')[""" + str(chart_idx) + """];
                if (!wrapper) return {text: '', transform: ''};
                const tooltip = wrapper.querySelector('.recharts-tooltip-wrapper');
                if (!tooltip) return {text: '', transform: ''};
                return {
                    text: tooltip.innerText || '',
                    transform: window.getComputedStyle(tooltip).transform || ''
                };
            }""")
            
            if not tooltip_before['text'] and not tooltip_before['transform']:
                # Tooltip not found
                wrapper_html = page_d.evaluate("""() => {
                    const wrapper = document.querySelectorAll('.recharts-wrapper')[""" + str(chart_idx) + """];
                    return wrapper ? wrapper.outerHTML.substring(0, 300) : '';
                }""")
                print(f"| ❌ D.3.{chart_idx+1} - ArrowRight changes content          | False    | No .recharts-tooltip-wrapper found")
                print(f"     HTML: {wrapper_html}")
                all_passed = False
                continue
            
            # Press ArrowRight twice (150ms between)
            page_d.keyboard.press("ArrowRight")
            page_d.wait_for_timeout(150)
            page_d.keyboard.press("ArrowRight")
            page_d.wait_for_timeout(50)
            
            # Get tooltip info AFTER
            tooltip_after = page_d.evaluate("""() => {
                const wrapper = document.querySelectorAll('.recharts-wrapper')[""" + str(chart_idx) + """];
                if (!wrapper) return {text: '', transform: ''};
                const tooltip = wrapper.querySelector('.recharts-tooltip-wrapper');
                if (!tooltip) return {text: '', transform: ''};
                return {
                    text: tooltip.innerText || '',
                    transform: window.getComputedStyle(tooltip).transform || ''
                };
            }""")
            
            # Check if changed
            d3_result = (tooltip_before['text'] != tooltip_after['text'] or 
                        tooltip_before['transform'] != tooltip_after['transform'])
            
            check_d3_result = print_check(
                f"D.3.{chart_idx+1} - ArrowRight changes content",
                d3_result,
                f"Before: '{tooltip_before['text'][:20]}...' After: '{tooltip_after['text'][:20]}...'"
            )
            all_passed &= check_d3_result
            if d3_result:
                d3_passed_count += 1
        
        page_d.close()
        
        # ===== CHECK E: Error State with ARIA Alert (on new page) =====
        page_e = new_page(browser)
        page_e.goto(BASE_URL)
        page_e.wait_for_load_state("networkidle")
        
        # Register error handler BEFORE routing
        def handle_error_route(route):
            if API_METRICS_PATH in route.request.url:
                route.abort()
            else:
                route.continue_()
        
        page_e.route("**/*", handle_error_route)
        
        # Reload to trigger the API call
        page_e.reload(wait_until="domcontentloaded")
        page_e.wait_for_timeout(500)
        
        # Look for visible alert with text
        alerts = page_e.locator("[role='alert']").all()
        alert_text = ""
        alert_has_spanish_lang = False
        alert_visible = False
        
        for alert in alerts:
            if alert.is_visible():
                text = alert.inner_text().strip()
                if text:
                    alert_visible = True
                    alert_text = text
                    
                    # Check lang attribute on alert or closest ancestor
                    lang_attr = alert.evaluate("""el => {
                        return el.getAttribute('lang') || el.closest('[lang]')?.getAttribute('lang');
                    }""")
                    alert_has_spanish_lang = (lang_attr == "es")
                    break
        
        check_e1 = print_check(
            "E.1 - Error alert visible with text",
            alert_visible,
            f"Text: '{alert_text[:60]}...'" if alert_text else "No alert"
        )
        all_passed &= check_e1
        
        check_e2 = print_check(
            "E.2 - Alert has lang='es'",
            alert_has_spanish_lang,
            f"lang='es': {alert_has_spanish_lang}"
        )
        all_passed &= check_e2
        
        page_e.unroute("**/*")
        page_e.close()
        
        # ===== CHECK F: Loading State, Skeleton, CLS =====
        page_f = new_page(browser)
        
        # Route-holding mechanism
        held_routes = []
        def handle_held_route(route):
            if API_METRICS_PATH in route.request.url:
                held_routes.append(route)
            else:
                route.continue_()
        
        page_f.route(re.compile(r".*/api/metrics"), handle_held_route)
        page_f.goto(BASE_URL, wait_until="commit")
        
        # Wait for route to be held (max 5s)
        wait_attempts = 0
        while len(held_routes) < 1 and wait_attempts < 50:
            page_f.wait_for_timeout(100)
            wait_attempts += 1
        
        if len(held_routes) < 1:
            print(f"| ❌ F.Pre - /api/metrics requested         | False    | No petición a /api/metrics")
            check_f_pre = False
            all_passed = False
        else:
            check_f_pre = True
        
        # F.1: Check aria-busy sections
        busy_sections = page_f.locator("section[aria-busy='true']").all()
        check_f1 = print_check(
            "F.1 - aria-busy section exists",
            len(busy_sections) > 0,
            f"Found {len(busy_sections)} section(s)"
        )
        all_passed &= check_f1
        
        # F.2: Check for visible skeletons
        skeletons = page_f.locator("div[data-slot='skeleton']").all()
        skeleton_info = []
        for skeleton in skeletons:
            if skeleton.is_visible():
                bbox = skeleton.bounding_box()
                if bbox and bbox['height'] > 0:
                    skeleton_info.append(int(bbox['height']))
        
        if len(skeleton_info) == 0:
            # Print aria-busy section HTML for diagnosis
            section_html = page_f.evaluate("""() => {
                const section = document.querySelector('section[aria-busy="true"]');
                return section ? section.outerHTML.substring(0, 300) : 'no section found';
            }""")
            print(f"| ❌ F.2 - Skeletons visible               | False    | No visible skeletons found")
            print(f"     HTML: {section_html}")
            check_f2 = False
            all_passed = False
        else:
            check_f2 = print_check(
                "F.2 - Skeletons visible",
                True,
                f"Found {len(skeleton_info)}, heights: {skeleton_info[:3]}"
            )
        
        # F.3: Get section heights BEFORE and AFTER load
        # Note: 8 px threshold is heuristic; standard criterion is F.4 (CLS < 0.1)
        before_heights = page_f.evaluate("""() => {
            const sections = Array.from(document.querySelectorAll('section[aria-busy="true"]'));
            return sections.map((s, idx) => {
                const label = s.getAttribute('aria-label') || 
                             s.querySelector('h2')?.textContent ||
                             s.querySelector('[role="heading"]')?.textContent ||
                             'Section ' + idx;
                return {
                    idx: idx,
                    label: label.trim(),
                    height: s.getBoundingClientRect().height
                };
            });
        }""")
        
        # Release routes and wait for load
        page_f.wait_for_timeout(300)
        for route in held_routes:
            route.continue_()
        held_routes.clear()
        page_f.wait_for_load_state("networkidle")
        page_f.wait_for_timeout(300)
        
        # Measure heights of sections after load
        after_heights = page_f.evaluate("""() => {
            const sections = Array.from(document.querySelectorAll('section'));
            return sections.slice(0, 2).map((s, idx) => {
                const label = s.getAttribute('aria-label') || 
                             s.querySelector('h2')?.textContent ||
                             s.querySelector('[role="heading"]')?.textContent ||
                             'Section ' + idx;
                return {
                    idx: idx,
                    label: label.trim(),
                    height: s.getBoundingClientRect().height
                };
            });
        }""")
        
        # Print F.3 details and calculate deltas
        print("\n  F.3 Details (informative - heuristic threshold 8px, standard is CLS < 0.1):")
        height_deltas = []
        if len(before_heights) > 0 and len(after_heights) > 0:
            for i in range(min(len(before_heights), len(after_heights))):
                before = before_heights[i]['height']
                after = after_heights[i]['height']
                label = before_heights[i]['label']
                delta = abs(before - after)
                height_deltas.append(delta)
                print(f"    [{label}] Before: {int(before)}px, After: {int(after)}px, Delta: {int(delta)}px")
        
        # F.3 is informative (doesn't affect exit code)
        check_f3 = print_check(
            "F.3 - Layout shift <= 8px per section",
            all(d <= 8 for d in height_deltas) if height_deltas else False,
            f"Deltas: {[int(d) for d in height_deltas]} px - INFO"
        )
        
        # F.4: CLS value
        cls_value = page_f.evaluate("() => window.clsValue || 0")
        check_f4 = print_check(
            "F.4 - CLS < 0.1",
            cls_value < 0.1,
            f"CLS: {cls_value:.4f}"
        )
        all_passed &= check_f4
        
        # F.5: SR-only tables
        sr_tables = page_f.locator("table.sr-only").all()
        sr_table_rows = 0
        for table in sr_tables:
            rows = table.locator("tbody tr").count()
            sr_table_rows += rows
        
        check_f5 = print_check(
            "F.5 - SR-only tables with rows",
            len(sr_tables) > 0 and sr_table_rows > 0,
            f"Tables: {len(sr_tables)}, Rows: {sr_table_rows}"
        )
        all_passed &= check_f5
        
        page_f.unroute(re.compile(r".*/api/metrics"))
        page_f.close()
        
        # ===== CHECK G: Reduced Motion & No Animations =====
        page_g = new_page(browser, reduced_motion="reduce")
        
        # Route-holding mechanism (same as F)
        held_routes_g = []
        def handle_held_route_g(route):
            if API_METRICS_PATH in route.request.url:
                held_routes_g.append(route)
            else:
                route.continue_()
        
        page_g.route(re.compile(r".*/api/metrics"), handle_held_route_g)
        page_g.goto(BASE_URL, wait_until="commit")
        
        # Wait for route to be held (max 5s)
        wait_attempts_g = 0
        while len(held_routes_g) < 1 and wait_attempts_g < 50:
            page_g.wait_for_timeout(100)
            wait_attempts_g += 1
        
        # G.Pre: Check reduced-motion preference and skeletons
        reduced_motion_active = page_g.evaluate("() => window.matchMedia('(prefers-reduced-motion: reduce)').matches")
        
        g_skeletons = page_g.locator("div[data-slot='skeleton']").all()
        g_skeleton_visible_count = 0
        for skel in g_skeletons:
            if skel.is_visible():
                g_skeleton_visible_count += 1
        
        g_pre_result = reduced_motion_active and g_skeleton_visible_count >= 1
        
        check_g_pre = print_check(
            "G.Pre - reduced-motion=reduce + skeletons",
            g_pre_result,
            f"reduced-motion={reduced_motion_active}, skeletons={g_skeleton_visible_count}"
        )
        all_passed &= check_g_pre
        
        # G.1: Check animations in visible skeletons
        if g_skeleton_visible_count > 0:
            has_animations = page_g.evaluate("""() => {
                const elems = document.querySelectorAll('div[data-slot="skeleton"]');
                for (const elem of elems) {
                    if (!elem.offsetParent) continue;  // Skip hidden
                    const style = window.getComputedStyle(elem);
                    const anim_name = style.animationName || 'none';
                    if (anim_name !== 'none') {
                        return true;
                    }
                }
                return false;
            }""")
            
            check_g1 = print_check(
                "G.1 - No animations in visible skeletons",
                not has_animations,
                f"Animations: {has_animations}"
            )
            all_passed &= check_g1
        else:
            check_g1 = print_check(
                "G.1 - No animations in visible skeletons",
                False,
                "No visible skeletons to check"
            )
            all_passed = False
        
        # Release routes for G
        for route in held_routes_g:
            route.continue_()
        held_routes_g.clear()
        
        page_g.unroute(re.compile(r".*/api/metrics"))
        page_g.close()
        
        browser.close()
    
    print("|" + "-"*138 + "|")
    print("="*140)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
