/****************************************************************************
 *                              Sonar Ada Plugin                            *
 *                                                                          *
 *                        Copyright (C) 2014, AdaCore                       *
 *                                                                          *
 * This is free software;  you can redistribute it  and/or modify it  under *
 * terms of the  GNU General Public License as published  by the Free Soft- *
 * ware  Foundation;  either version 3,  or (at your option) any later ver- *
 * sion.  This software is distributed in the hope  that it will be useful, *
 * but WITHOUT ANY WARRANTY;  without even the implied warranty of MERCHAN- *
 * TABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public *
 * License for  more details.  You should have  received  a copy of the GNU *
 * General  Public  License  distributed  with  this  software;   see  file *
 * COPYING3.  If not, go to http://www.gnu.org/licenses for a complete copy *
 * of the license.                                                          *
 ****************************************************************************/

package org.sonar.plugins.ada.persistence;

import lombok.AllArgsConstructor;

/**
 * Enumeration of resource kind.
 */
@AllArgsConstructor
public enum ResourceKind {
  PROJECT (0), DIRECTORY (1), FILE (2);

  public final int img;
}