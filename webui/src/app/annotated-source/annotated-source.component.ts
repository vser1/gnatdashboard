import { CORE_DIRECTIVES } from '@angular/common';
import { Component } from '@angular/core';
import { DomSanitizationService, SafeHtml } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';

import { highlightAuto } from 'highlight.js';

import { GNAThubService } from '../gnathub.service';
import { IGNAThubBlob, IGNAThubBlobLine, IGNAThubMessage } from 'gnat';

import { Loader } from '../loader';
import { MapValues } from '../object.pipe';
import { MissingSourceError } from '../errors';

import '../array-utils';

@Component({
    selector: 'annotated-source',
    templateUrl: './annotated-source.template.html',
    styleUrls: [ './annotated-source.style.css' ],
    directives: [ CORE_DIRECTIVES, Loader, MissingSourceError ],
    pipes: [ MapValues ],
    providers: [ GNAThubService ]
})
export class AnnotatedSource {
    private filename: string = null;
    private blob: IGNAThubBlob = null;
    private isBlobFetchError: boolean = false;
    private htmlLines: { number: number, content: SafeHtml }[] = null;
    private htmlLinesOfBlob: IGNAThubBlob = null;

    constructor(
        private gnathub: GNAThubService,
        private route: ActivatedRoute,
        private sanitizer: DomSanitizationService) {}

    ngOnInit(): void {
        this.filename = this.route.snapshot.params['filename'];
        this.gnathub.getSource(this.filename).subscribe(
            blob => {
                for (let tool_id in blob.tools) {
                    // Show messages triggered by all tools by default
                    blob.tools[tool_id]['ui_selected'] = true;
                }
                for (let rule_id in blob.rules) {
                    // Show messages triggered by all rules by default
                    blob.rules[rule_id]['ui_selected'] = true;
                }
                this.blob = blob;
            },
            error => this.isBlobFetchError = !!error);
    }

    /**
     * @return The total number of displayed messages.
     */
    getMessageDisplayedCount():number {
        if (!this.blob) {
            return 0;
        }
        return Object.keys(this.blob.rules).sum(id => {
            const rule = this.blob.rules[id];
            if (rule.ui_selected && this.blob.tools[rule.tool.id].ui_selected) {
                return rule.message_count;
            }
            return 0;
        });
    }

    /**
     * Mark the input string as safe HTML (for use with [innerHTML]).
     *
     * @param value The input string.
     * @return The safe HTML.
     */
    private bypassSanitizer(value: string): SafeHtml {
        return this.sanitizer.bypassSecurityTrustHtml(value)
    }

    /**
     * Highlight the whole file and return an array of lines.
     *
     * @return An array of HTML string with highlighting markup, or |null| if
     *      the blob is not loaded.
     */
    highlightedLines(): { number: number, content: SafeHtml }[] {
        if (!this.blob || !this.blob.lines) {
            return [];
        }
        if (!this.htmlLines || this.htmlLinesOfBlob !== this.blob) {
            // Decorate the code with HTML markup for highlighting.
            // Pass all lines to |this.highlight| as a single string to provide
            // the highlight engine with as much context as possible (for
            // markups that span on several lines, eg. Python docstrings).
            // NOTE: The |string.replace| method is used to remove the extra
            // line otherwise introduced by the |string.split| method:
            //
            //      > 'line 1\nline 2\nline 3\n'.split(/\r\n|\r|\n/g)
            //      [ 'line 1', 'line 2', 'line 3', '' ]
            //
            // This ensures this method returns a consistent line count (so that
            // we don't need to check the line exists in |this.messages|.
            let i = 0;
            this.htmlLines = this.highlight(
                this.blob.lines.map(l => l.content).join('')
            ).replace(/(\r\n|\r|\n)$/, '').split(/\r\n|\r|\n/g).map(
                content => Object({
                    number: ++i,
                    content: this.bypassSanitizer(content)
                }));
            this.htmlLinesOfBlob = this.blob;
        }
        return this.htmlLines;
    }

    /**
     * Return the list of messages attached to the given line.
     *
     * @param line The line for which to list messages.
     * @return The list of messages.
     */
    messages(line: number): IGNAThubMessage[] {
        if (!this.blob || !this.blob.lines) {
            return [];
        }
        return this.blob.lines[line - 1].messages;
    }

    /**
     * Return the coverage value for for the given line.
     *
     * @param line The line for which to get coverage information.
     * @return The coverage value.
     */
    coverage(line: number): string {
        if (!this.blob || !this.blob.lines) {
            return '';
        }
        return this.blob.lines[line - 1].coverage;
    }

    /**
     * Syntax highlight a code snippet.
     *
     * @param code The source code to highlight.
     * @return The HTML string with highlighting markup.
     */
    highlight(code: string): string {
        return highlightAuto(code).value;
    }
}
